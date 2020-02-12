import json
import logging

from api.models import *
from api.common.ratio import _get_dim_amount
from .response_parser import parse_pricing_response

logger = logging.getLogger("dme_api")


def is_in_zone(zone_code, suburb, postal_code, state):
    zones = FP_zones.objects.filter(zone=zone_code)

    if zones:
        for zone in zones:
            if zone.suburb and zone.suburb.lower() != suburb:
                continue
            if zone.postal_code and zone.postal_code.lower() != postal_code:
                continue
            if zone.state and zone.state.lower() != state:
                continue

            return True

    return False


def address_filter(booking, rules):
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

        if rule.pu_state and rule.pu_state.lower() != pu_postal_code:
            continue

        if rule.de_state and rule.de_state.lower() != de_postal_code:
            continue

        if rule.pu_zone:
            if not is_in_zone(rules.pu_zone, pu_suburb, pu_postal_code, pu_state):
                continue

        if rule.de_zone:
            if not is_in_zone(rule.de_zone, de_suburb, de_postal_code, de_state):
                continue

        filtered_rule_ids.append(rule.id)

    return rules.filter(pk__in=filtered_rule_ids)


def find_vehicle(booking, fp):
    vehicles = FP_vehicles.objects.filter(freight_provider_id=fp.id)
    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    if len(booking_lines) == 0:
        logger.info(f"@832 Century - no Booking Lines to deliver")
        return

    try:
        sum_cube = 0
        max_width = 0
        max_height = 0
        max_length = 0
        vehicle_ids = []

        for item in booking_lines:
            length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength * 5
            width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth * 5
            height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight * 5

            # Take the largest length, width and height on the largest package
            if max_length < length:
                max_length = length

            if max_width < width:
                max_width = width

            if max_height < height:
                max_height = height

            # Work out the cube of all the packages and add together
            cube = width * height * length
            sum_cube += cube * item.e_qty

        # print(f"Max width = {max_width}")
        # print(f"Max height = {max_height}")
        # print(f"Max length = {max_length}")
        # print(f"Sum Cube = {sum_cube}")

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
        logger.info(f"@833 Century - error while find vehicle")
        return


def dim_filter(fp, booking, rules):
    filtered_rules = []

    if fp.fp_company_name.lower() == "century":
        vehicle_ids = find_vehicle(booking, fp)

        if not vehicle_ids:
            logger.info(f"@834 Century - no proper vehicles")
            return

        rules = rules.filter(vehicle_id__in=vehicle_ids)
        return rules


def get_pricing(fp_name, booking):
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    rules = FP_pricing_rules.objects.filter(freight_provider_id=fp.id)

    # Address Filter
    rules = address_filter(booking, rules)

    if not rules:
        logger.info(f"@831 Century - not supported addresses")
        return

    # Size(dim) Filter
    rules = dim_filter(fp, booking, rules)
    costs = FP_costs.objects.filter(pk__in=[rule.cost_id for rule in rules]).order_by(
        "per_UOM_charge"
    )

    if fp.fp_company_name.lower() == "century":  # If FP's Charge UOM is `vehicle`
        costs = costs[: fp.prices_count]

    pricies = []
    for cost in costs:
        rule = rules.get(cost_id=cost.id)
        etd = (
            f"{rule.timing.min}, {rule.timing.max}"
            if rule.timing.max
            else f"{rule.timing.min}"
        )
        price = {
            "netPrice": cost.per_UOM_charge,
            "totalTaxes": 0,
            "service_name": f"{rule.service_timing_code}",
            "etd": etd,
            "fk_freight_provider_id": fp.id,
        }
        pricies.append(price)

    return {
        "price": pricies,
        "requestId": "Centry-DME",
    }
