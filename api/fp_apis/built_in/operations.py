import logging
import os
import json
import requests

from django.db.models import Q

from api.models import FP_zones, FP_vehicles
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.common import trace_error
from api.common.constants import PALLETS
from api.common.pallet import lines_to_dict


logger = logging.getLogger(__name__)


def get_zone_code(postal_code, fp):
    zones = (
        FP_zones.objects.filter(fk_fp=fp.id)
        .filter(
            Q(postal_code=postal_code)
            | Q(start_postal_code__lte=postal_code, end_postal_code__gte=postal_code)
        )
        .only("zone")
    )

    if zones.exists():
        return zones.first().zone


def get_zone(fp, state, postal_code, suburb):
    zones = FP_zones.objects.filter(
        state=state, postal_code=postal_code, suburb=suburb, fk_fp=fp.id
    )

    if zones:
        return zones.first()

    return None


def is_in_zone(fp, zone_code, suburb, postal_code, state, avail_zones):
    # logger.info(f"#820 {fp}, {zone_code}, {suburb}, {postal_code}, {state}, {avail_zones}")

    for avail_zone in avail_zones:
        if avail_zone.zone == zone_code:
            return True

    return False


def address_filter(booking, booking_lines, rules, fp):
    LOG_ID = "[BP addr filter]"
    pu_suburb = booking.pu_Address_Suburb.lower()
    pu_postal_code = booking.pu_Address_PostalCode.lower()
    pu_state = booking.pu_Address_State.lower()

    de_suburb = booking.de_To_Address_Suburb.lower()
    de_postal_code = booking.de_To_Address_PostalCode.lower()
    de_state = booking.de_To_Address_State.lower()

    # Zone
    found_pu_zone = None
    found_de_zone = None
    avail_pu_zones = FP_zones.objects.filter(fk_fp=fp.id)
    avail_de_zones = FP_zones.objects.filter(fk_fp=fp.id)
    if pu_state:
        avail_pu_zones = avail_pu_zones.filter(state__iexact=pu_state)
    if pu_postal_code:
        avail_pu_zones = avail_pu_zones.filter(postal_code=pu_postal_code)
    if pu_suburb:
        avail_pu_zones = avail_pu_zones.filter(suburb__iexact=pu_suburb)
    if de_state:
        avail_de_zones = avail_de_zones.filter(state__iexact=de_state)
    if de_postal_code:
        avail_de_zones = avail_de_zones.filter(postal_code=de_postal_code)
    if de_suburb:
        avail_de_zones = avail_de_zones.filter(suburb__iexact=de_suburb)

    filtered_rule_ids = []
    for rule in rules:
        if rule.pu_suburb and rule.pu_suburb.lower() != pu_suburb:
            # logger.info(f"@850 {LOG_ID} PU Suburb does not match")
            continue

        if rule.de_suburb and rule.de_suburb.lower() != de_suburb:
            # logger.info(f"@851 {LOG_ID} DE Suburb does not match")
            continue

        if rule.pu_postal_code and rule.pu_postal_code.lower() != pu_postal_code:
            # logger.info(f"@852 {LOG_ID} PU PostalCode does not match")
            continue

        if rule.de_postal_code and rule.de_postal_code.lower() != de_postal_code:
            # logger.info(f"@853 {LOG_ID} DE PostalCode does not match")
            continue

        if rule.pu_state and rule.pu_state.lower() != pu_state:
            # logger.info(f"@854 {LOG_ID} PU State does not match")
            continue

        if rule.de_state and rule.de_state.lower() != de_state:
            # logger.info(f"@855 {LOG_ID} DE State does not match")
            continue

        if rule.pu_zone and avail_pu_zones.exists():
            if found_pu_zone and found_pu_zone != rule.pu_zone:
                continue

            if not is_in_zone(
                fp, rule.pu_zone, pu_suburb, pu_postal_code, pu_state, avail_pu_zones
            ):
                # logger.info(f"@856 {LOG_ID} PU Zone does not match")
                continue

        if rule.de_zone and avail_de_zones.exists():
            if found_de_zone and found_de_zone != rule.de_zone:
                continue

            if not is_in_zone(
                fp, rule.de_zone, de_suburb, de_postal_code, de_state, avail_de_zones
            ):
                # logger.info(f"@857 {LOG_ID} DE Zone does not match")
                continue

        found_pu_zone = rule.pu_zone
        found_de_zone = rule.de_zone
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


def vehicles_to_dict(vehicles):
    vehicles_dict = []
    for vehicle in vehicles:
        vehicles_dict.append(
            {
                "w": _get_dim_amount(vehicle.dim_UOM) * vehicle.max_width,
                "h": _get_dim_amount(vehicle.dim_UOM) * vehicle.max_height,
                "d": _get_dim_amount(vehicle.dim_UOM) * vehicle.max_length,
                "max_wg": vehicle.max_mass,
                "id": vehicle.id,
            }
        )

    return vehicles_dict


def lines_to_vehicle(lines_dict, vehicles_dict):
    data = {
        "bins": vehicles_dict,
        "items": lines_dict,
        "username": os.environ["3D_PACKING_API_USERNAME"],
        "api_key": os.environ["3D_PACKING_API_KEY"],
        "params": {
            "images_background_color": "255,255,255",
            "images_bin_border_color": "59,59,59",
            "images_bin_fill_color": "230,230,230",
            "images_item_border_color": "214,79,79",
            "images_item_fill_color": "177,14,14",
            "images_item_back_border_color": "215,103,103",
            "images_sbs_last_item_fill_color": "99,93,93",
            "images_sbs_last_item_border_color": "145,133,133",
            "images_width": 100,
            "images_height": 100,
            "images_source": "file",
            "images_sbs": 1,
            "stats": 1,
            "item_coordinates": 1,
            "images_complete": 1,
            "images_separated": 1,
        },
    }
    url = f"{os.environ['3D_PACKING_API_URL']}/packer/pack"
    response = requests.post(url, data=json.dumps(data))
    res_data = response.json()["response"]
    if res_data["status"] == -1:
        msg = ""
        for error in res_data["errors"]:
            msg += f"{error['message']} \n"
        logger.info(f"Packing API Error: {msg}")

    return res_data


def find_vehicle_ids(booking_lines, fp):
    vehicles = FP_vehicles.objects.filter(freight_provider_id=fp.id)

    if len(booking_lines) == 0:
        logger.info(f"@832 Rule Type 01 - no Booking Lines to deliver")
        return
    
    try:
        # prepare vehicles data
        vehicles_dict = vehicles_to_dict(vehicles)

        # prepare lines data
        lines_dict = lines_to_dict(booking_lines)

        packed_results = lines_to_vehicle(lines_dict, vehicles_dict)
        vehicle_ids = []
        for bin_packed in packed_results['bins_packed']:
            if not bin_packed['not_packed_items']:
                vehicle_ids.append(int(bin_packed['bin_data']['id']))

        # Century Exceptional Rule #1
        if fp.fp_company_name.upper() == "CENTURY":
            """
            The load maybe on a pallet but the 1.5m length does not apply to the pallets.
            A pallet larger than the standard 1.2m x 1.2m must booked as a 1 tonne job.
            """
            has_pallet = False
            _vehicle_ids = []

            for line in booking_lines:
                if (
                    line.e_type_of_packaging
                    and line.e_type_of_packaging.upper() in PALLETS
                    and (max_length > 1.2 or max_width > 1.2)
                ):
                    has_pallet = True
                    break

            if has_pallet:
                for vehicle_id in vehicle_ids:
                    non_pallet_ids = [63, 64, 65, 66, 67, 68, 69, 70]

                    if not vehicle_id in non_pallet_ids:
                        _vehicle_ids.append(vehicle_id)

                vehicle_ids = _vehicle_ids

        return vehicle_ids
    except Exception as e:
        trace_error.print()
        logger.info(f"@833 Rule Type 01 - error while find vehicle. Error: {str(e)}")
        return


def get_booking_lines_weight(booking_lines):
    weight = 0

    for item in booking_lines:
        weight += (
            item.e_qty * item.e_weightPerEach * _get_weight_amount(item.e_weightUOM)
        )

    return weight


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

        if cost.max_length:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.max_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.max_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.max_height

        if cost.price_up_to_width:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_height

        comp_count = 0
        for item in booking_lines:
            if not item.e_type_of_packaging or (
                item.e_type_of_packaging
                and not item.e_type_of_packaging.upper() in PALLETS
            ):
                logger.info(
                    f"@833 {fp.fp_company_name} - only support `Pallet`. Current is `{item.e_type_of_packaging}`"
                )
                return
            else:
                width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
                height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight
                length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength

                if width <= c_width and height <= c_height and length <= c_length:
                    comp_count += 1

        if comp_count == len(booking_lines):
            rule_ids.append(rule.id)

    return rule_ids


def find_rule_ids_by_weight(booking_lines, rules, fp):
    rule_ids = []

    for rule in rules:
        cost = rule.cost
        c_weight = 0

        # Check if only for PALLET
        if (
            cost.UOM_charge.upper() in PALLETS
            and not booking_line.e_type_of_packaging.upper() in PALLETS
        ):
            logger.info(
                f"@833 {fp.fp_company_name} - rule({rule.pk}) only support `Pallet`"
            )
            continue

        if cost.max_weight:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.max_weight

        if cost.price_up_to_weight:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.price_up_to_weight

        qty = 0
        total_weight = 0
        for booking_line in booking_lines:
            weight = (
                booking_line.e_qty
                * _get_weight_amount(booking_line.e_weightUOM)
                * booking_line.e_weightPerEach
            )
            total_weight += weight
            qty += booking_line.e_qty

        if cost.UOM_charge.upper() in PALLETS:
            if cost.end_qty and cost.end_qty < qty:
                continue
            if cost.start_qty and cost.start_qty >= qty:
                continue
        else:
            if cost.end_qty and cost.end_qty < total_weight:
                continue
            if cost.start_qty and cost.start_qty >= total_weight:
                continue

        if c_weight and total_weight > c_weight:
            continue

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
        logger.info(f"#820 DIM FILTER vehicles: {vehicle_ids}")

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
