import logging

from api.models import FP_zones, FP_vehicles
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.common import trace_error
from api.common.constants import PALLETS


logger = logging.getLogger(__name__)


def get_zone(fp, state, postal_code, suburb):
    zones = FP_zones.objects.filter(
        state=state, postal_code=postal_code, suburb=suburb, fk_fp=fp.id
    )

    if zones:
        return zones.first()

    return None


def is_in_zone(fp, zone_code, suburb, postal_code, state):
    # logger.info(f"#820 {fp}, {zone_code}, {suburb}, {postal_code}, {state}")
    zones = FP_zones.objects.filter(zone__iexact=zone_code, fk_fp=fp.id)
    # logger.info(f"#821 {zones.count()}")

    if not zones:
        return False

    for zone in zones:
        # logger.info(f"#822 {zone}")

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


def address_filter(booking, booking_lines, rules, fp):
    LOG_ID = "[BP addr filter]"
    pu_suburb = booking.pu_Address_Suburb.lower()
    pu_postal_code = booking.pu_Address_PostalCode.lower()
    pu_state = booking.pu_Address_State.lower()

    de_suburb = booking.de_To_Address_Suburb.lower()
    de_postal_code = booking.de_To_Address_PostalCode.lower()
    de_state = booking.de_To_Address_State.lower()

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

        if rule.pu_zone:
            if not is_in_zone(fp, rule.pu_zone, pu_suburb, pu_postal_code, pu_state):
                # logger.info(f"@856 {LOG_ID} PU Zone does not match")
                continue

        if rule.de_zone:
            if not is_in_zone(fp, rule.de_zone, de_suburb, de_postal_code, de_state):
                # logger.info(f"@857 {LOG_ID} DE Zone does not match")
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

        # 2021-07-07 Century only charge per vehicle
        # if (
        #     booking_lines.first().e_type_of_packaging
        #     and booking_lines.first().e_type_of_packaging.lower() in PALLETS
        # ):
        #     for vehicle in vehicles:
        #         vmax_width = (
        #             _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_width
        #         )
        #         vmax_height = (
        #             _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_height
        #         )
        #         vmax_length = (
        #             _get_dim_amount(vehicle.pallet_UOM) * vehicle.max_pallet_length
        #         )

        #         if (
        #             vmax_width >= max_width
        #             and max_height >= max_height
        #             and vmax_length >= max_length
        #             and vehicle.pallets >= len(booking_lines)
        #         ):
        #             vehicle_ids.append(vehicle.id)
        # else:
        #     for vehicle in vehicles:
        #         vmax_width = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_width
        #         vmax_height = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_height
        #         vmax_length = _get_dim_amount(vehicle.dim_UOM) * vehicle.max_length
        #         vehicle_cube = vmax_width * vmax_height * vmax_length

        #         if (
        #             vmax_width >= max_width
        #             and max_height >= max_height
        #             and vmax_length >= max_length
        #             and vehicle_cube * 0.8 >= sum_cube
        #         ):
        #             vehicle_ids.append(vehicle.id)

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
                    and line.e_type_of_packaging.lower() in PALLETS
                    and (max_length > 1.2 or max_width > 1.2)
                ):
                    has_pallet = True
                    break

            for vehicle_id in vehicle_ids:
                if not vehicle_id in [1, 2, 3, 22, 23, 24, 25]:
                    _vehicle_ids.append(vehicle_id)

            vehicle_ids = _vehicle_ids

        return vehicle_ids
    except Exception as e:
        trace_error.print()
        logger.info(f"@833 Rule Type 01 - error while find vehicle. Error: {str(e)}")
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

        if cost.max_length:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.max_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.max_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.max_height

        if cost.oversize_price and cost.price_up_to_width:
            c_width = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_width
            c_length = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_length
            c_height = _get_dim_amount(cost.dim_UOM) * cost.price_up_to_height

        comp_count = 0
        for item in booking_lines:
            if not item.e_type_of_packaging or (
                item.e_type_of_packaging
                and not item.e_type_of_packaging.lower() in PALLETS
            ):
                logger.info(f"@833 {fp.fp_company_name} - only support `Pallet`")
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

        if cost.max_weight:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.max_weight

        if cost.oversize_price and cost.price_up_to_weight:
            c_weight = _get_weight_amount(cost.weight_UOM) * cost.price_up_to_weight

        comp_count = 0
        for booking_line in booking_lines:
            if (
                cost.UOM_charge.lower() in PALLETS
                and not booking_line.e_type_of_packaging.lower() in PALLETS
            ):
                logger.info(f"@833 {fp.fp_company_name} - only support `Pallet`")
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
