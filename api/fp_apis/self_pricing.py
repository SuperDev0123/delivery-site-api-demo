import json
import logging
import traceback

from api.models import *
from api.common.ratio import _get_dim_amount, _get_weight_amount, _m3_to_kg
from .response_parser import parse_pricing_response
from .payload_builder import BUILT_IN_PRICINGS

logger = logging.getLogger("dme_api")
PALLETS = ["pallet", "plt"]


def is_in_zone(fp, zone_code, suburb, postal_code, state):
    zones = FP_zones.objects.filter(zone=zone_code, fk_fp=fp.id)

    if zones:
        for zone in zones:
            if zone.suburb and zone.suburb.lower() != suburb:
                continue
            if zone.postal_code and zone.postal_code.lower() != postal_code:
                continue
            if zone.state and zone.state.lower() != state:
                continue
            if (
                zone.start_postal_code
                and zone.end_postal_code
                and postal_code
                and int(postal_code) < int(zone.start_postal_code)
                and int(postal_code) > int(zone.end_postal_code)
            ):
                continue

            return True

    return False


def address_filter(booking, booking_lines, rules, fp):
    pu_suburb = booking.pu_Address_Suburb.lower()
    pu_postal_code = booking.pu_Address_PostalCode.lower()
    pu_state = booking.pu_Address_State.lower()

    de_suburb = booking.de_To_Address_Suburb.lower()
    de_postal_code = booking.de_To_Address_PostalCode.lower()
    de_state = booking.de_To_Address_State.lower()

    filtered_rule_ids = []
    for rule in rules:
        if rule.pu_suburb and rule.pu_suburb.lower() != pu_suburb:
            continue

        if rule.de_suburb and rule.de_suburb.lower() != de_suburb:
            continue

        if rule.pu_postal_code and rule.pu_postal_code.lower() != pu_postal_code:
            continue

        if rule.de_postal_code and rule.de_postal_code.lower() != de_postal_code:
            continue

        if rule.pu_state and rule.pu_state.lower() != pu_state:
            continue

        if rule.de_state and rule.de_state.lower() != de_state:
            continue

        if rule.pu_zone:
            if not is_in_zone(fp, rule.pu_zone, pu_suburb, pu_postal_code, pu_state):
                continue

        if rule.de_zone:
            if not is_in_zone(fp, rule.de_zone, de_suburb, de_postal_code, de_state):
                continue

        filtered_rule_ids.append(rule.id)

    for rule in rules:
        if rule.both_way:
            if rule.pu_suburb and rule.pu_suburb.lower() != de_suburb:
                continue

            if rule.de_suburb and rule.de_suburb.lower() != pu_suburb:
                continue

            if rule.pu_postal_code and rule.pu_postal_code.lower() != de_postal_code:
                continue

            if rule.de_postal_code and rule.de_postal_code.lower() != pu_postal_code:
                continue

            if rule.pu_state and rule.pu_state.lower() != de_state:
                continue

            if rule.de_state and rule.de_state.lower() != pu_state:
                continue

            if rule.pu_zone:
                if not is_in_zone(
                    fp, rule.pu_zone, de_suburb, de_postal_code, de_state
                ):
                    continue

            if rule.de_zone:
                if not is_in_zone(
                    fp, rule.de_zone, pu_suburb, pu_postal_code, pu_state
                ):
                    continue

            filtered_rule_ids.append(rule.id)

    return rules.filter(pk__in=filtered_rule_ids)


def find_vehicle_ids(booking_lines, fp):
    vehicles = FP_vehicles.objects.filter(freight_provider_id=fp.id)

    if len(booking_lines) == 0:
        logger.info(f"@832 Rule Type 01 - no Booking Lines to deliver")
        return

    try:
        sum_cube = 0
        max_length = 0
        max_width = 0
        max_height = 0
        vehicle_ids = []

        for item in booking_lines:
            length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength
            width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
            height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight

            max_length = length if max_length < length else max_length
            max_width = width if max_width < width else max_width
            max_height = height if max_height < height else max_height
            sum_cube += width * height * length * item.e_qty

        # print(
        #     f"Max width: {max_width}, height: {max_height}, length: {max_length}, Sum Cube = {sum_cube}"
        # )

        if (
            booking_lines.first().e_type_of_packaging
            and booking_lines.first().e_type_of_packaging.lower() in PALLETS
        ):
            for vehicle in vehicles:
                vmax_width = (
                    _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_width
                )
                vmax_height = (
                    _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_height
                )
                vmax_length = (
                    _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_length
                )

                if (
                    vmax_width >= max_width
                    and max_height >= max_height
                    and vmax_length >= max_length
                    and vehicle.pallets >= len(booking_lines)
                ):
                    vehicle_ids.append(vehicle.id)
        else:
            for vehicle in vehicles:
                vmax_width = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_width
                vmax_height = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_height
                vmax_length = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_length
                vehicle_cube = vmax_width * vmax_height * vmax_length

                if (
                    vmax_width >= max_width
                    and max_height >= max_height
                    and vmax_length >= max_length
                    and vehicle_cube * 0.8 >= sum_cube
                ):
                    vehicle_ids.append(vehicle.id)

        return vehicle_ids
    except Exception as e:
        logger.info(f"@833 Rule Type 01 - error while find vehicle")
        return


def get_booking_lines_count(booking_lines):
    cnt = 0

    for item in booking_lines:
        cnt += item.e_qty

    return cnt


def find_rule_ids_by_dim(booking_lines, rules, fp):
    rule_ids = []

    for rule in rules:
        cost = rule.cost

        if cost.UOM_charge in PALLETS:  # Pallet Count Filter
            pallet_cnt = get_booking_lines_count(booking_lines)

            if cost.start_qty and cost.start_qty > pallet_cnt:
                continue
            if cost.end_qty and cost.end_qty < pallet_cnt:
                continue

        if cost.oversize_price and cost.max_length:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.max_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.max_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.max_height
        else:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_height

        comp_count = 0
        for item in booking_lines:
            if not item.e_type_of_packaging or (
                item.e_type_of_packaging
                and not item.e_type_of_packaging.lower() in PALLETS
            ):
                logger.error(f"@833 {fp.fp_company_name} - only support `Pallet`")
                return
            else:
                width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
                height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight
                length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength

                if width < c_width and height < c_height and length < c_length:
                    comp_count += 1

        if comp_count == len(booking_lines):
            rule_ids.append(rule.id)

    return rule_ids


def find_rule_ids_by_weight(booking_lines, rules, fp):
    rule_ids = []

    for rule in rules:
        cost = rule.cost

        if cost.oversize_price and cost.max_weight:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.max_weight
        else:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.price_up_to_weight

        comp_count = 0
        for booking_line in booking_lines:
            if (
                cost.UOM_charge.lower() in PALLETS
                and not booking_line.e_type_of_packaging.lower() in PALLETS
            ):
                logger.error(f"@833 {fp.fp_company_name} - only support `Pallet`")
                return
            else:
                total_weight = (
                    booking_line.e_qty
                    * _get_weight_amount(booking_line.e_weightUOM)
                    * booking_line.e_weightPerEach
                )

                if total_weight < c_weight:
                    comp_count += 1

        if comp_count == len(booking_lines):
            rule_ids.append(rule.id)

    return rule_ids


def is_oversize(booking_lines, rule):
    cost = rule.cost

    if cost.oversize_price and cost.max_length:
        c_width = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_width
        c_length = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_length
        c_height = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_height

        for item in booking_lines:
            width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
            height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight
            length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength

            if width >= c_width or height >= c_height or length >= c_length:
                return True

    return False


def is_overweight(booking_lines, rule):
    cost = rule.cost

    if cost.oversize_price and cost.max_weight:
        c_weight = _get_weight_amount(cost.weight_UOM) * cost.price_up_to_weight

        for booking_line in booking_lines:
            total_weight = (
                booking_line.e_qty
                * _get_weight_amount(booking_line.e_weightUOM)
                * booking_line.e_weightPerEach
            )

            if total_weight >= c_weight:
                return True

    return False


def dim_filter(booking, booking_lines, rules, fp):
    filtered_rules = []

    if fp.rule_type.rule_type_code in ["rule_type_01"]:  # Vehicle
        vehicle_ids = find_vehicle_ids(booking_lines, fp)

        if vehicle_ids:
            rules = rules.filter(vehicle_id__in=vehicle_ids)
            filtered_rules = rules
    elif fp.rule_type.rule_type_code in ["rule_type_02"]:  # Over size & Normal size
        rule_ids = find_rule_ids_by_dim(booking_lines, rules, fp)

        if rule_ids:
            filtered_rules = rules.filter(pk__in=rule_ids)

    return filtered_rules


def weight_filter(booking_lines, rules, fp):
    filtered_rules = []

    if fp.rule_type.rule_type_code in ["rule_type_02"]:  # Over weight & Normal weight
        rule_ids = find_rule_ids_by_weight(booking_lines, rules, fp)
        filtered_rules = rules.filter(pk__in=rule_ids)

    return filtered_rules


def find_cost(booking_lines, rules, fp):
    lowest_cost = None

    for rule in rules:
        cost = rule.cost

        if is_oversize(booking_lines, rule) or is_overweight(booking_lines, rule):
            per_UOM_charge = cost.oversize_price
        else:
            per_UOM_charge = cost.per_UOM_charge

        if not lowest_cost or per_UOM_charge < lowest_cost.per_UOM_charge:
            lowest_cost = cost

    return lowest_cost


def get_pricing(fp_name, booking):
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    pricies = []
    for service_type in service_types:
        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id, service_timing_code__iexact=service_type
        )

        # Address Filter
        rules = address_filter(booking, booking_lines, rules, fp)

        if not rules:
            logger.info(f"@831 {fp_name.upper()} - not supported addresses")
            continue

        # Size(dim) Filter
        if fp.rule_type.rule_type_code in ["rule_type_01", "rule_type_02"]:
            rules = dim_filter(booking, booking_lines, rules, fp)

            if not rules:
                continue

        if fp.rule_type.rule_type_code in ["rule_type_01"]:
            # Booking Qty of the Matching 'Charge UOM' x 'Per UOM Charge'
            cost = (
                FP_costs.objects.filter(pk__in=[rule.cost_id for rule in rules])
                .order_by("per_UOM_charge")
                .first()
            )
            net_price = cost.per_UOM_charge
        elif fp.rule_type.rule_type_code in ["rule_type_02"]:
            # Booking Qty of the Matching 'Charge UOM' x 'Per UOM Charge
            rules = weight_filter(booking_lines, rules, fp)
            cost = find_cost(booking_lines, rules, fp)
            net_price = cost.per_UOM_charge * get_booking_lines_count(booking_lines)
        elif fp.rule_type.rule_type_code in ["rule_type_03"]:
            # Greater of 1) or 2)
            # 1) 'Basic Charge' + (Booking Qty of the matching 'Charge UOM' x 'Per UOM Charge')
            # 2) 'Basic Charge' + ((Length in meters x width in meters x height in meters x 'M3 to KG Factor)
            #    x 'Per UOM Charge')
            cost = rules.first().cost
            price1 = get_booking_lines_count(booking_lines) * cost.per_UOM_charge
            price2 = (
                _m3_to_kg(booking_lines, cost.m3_to_kg_factor) * cost.per_UOM_charge
            )
            price0 = price1 if price1 > price2 else price2
            price0 += cost.basic_charge
            net_price = price0 if price0 > cost.min_charge else cost.min_charge

        rule = rules.get(cost_id=cost.id)
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_timing_code}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return {
        "price": pricies,
        "requestId": "",
    }
