import logging
import traceback

from api.models import (
    Fp_freight_providers,
    Booking_lines,
    FP_pricing_rules,
    FP_costs,
    FP_zones,
)
from api.common.ratio import _m3_to_kg
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.common.constants import PALLETS

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines, pu_zones, de_zones):
    LOG_ID = "[BIP TOLL]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]

    has_pallet = False
    has_carton = False
    for booking_line in booking_lines:
        if booking_line.e_type_of_packaging.upper() in PALLETS:
            has_pallet = True
        else:
            has_carton = True

    if has_pallet and has_carton:
        logger.info(f"{LOG_ID} Not supported --- has both Pallet and Carton")
    else:
        if has_pallet:
            logger.info(f"{LOG_ID} Pallet")
        else:
            logger.info(f"{LOG_ID} Carton")

    pricies = []
    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")
        rules = FP_pricing_rules.objects.filter(freight_provider_id=fp.id)
        rules = rules.filter(service_type__iexact=service_type)
        rules = rules.order_by("id")

        _rules = []
        for rule in rules:
            if has_carton and rule.cost.UOM_charge == "Kilogram":
                _rules.append(rule)
            if has_pallet and rule.cost.UOM_charge == "Pallet":
                _rules.append(rule)
        rules = _rules

        # Address Filter
        pu_postal_code = booking.pu_Address_PostalCode.zfill(4)
        de_postal_code = booking.de_To_Address_PostalCode.zfill(4)
        avail_pu_zones = FP_zones.objects.filter(fk_fp=fp.id)
        avail_de_zones = FP_zones.objects.filter(fk_fp=fp.id)
        avail_pu_zone, avail_de_zone = None, None
        if pu_postal_code:
            avail_pu_zones = avail_pu_zones.filter(postal_code=pu_postal_code)
            avail_pu_zone = avail_pu_zones.first().zone
        if de_postal_code:
            avail_de_zones = avail_de_zones.filter(postal_code=de_postal_code)
            avail_de_zone = avail_de_zones.first().zone

        if not avail_pu_zone or not avail_de_zone:
            logger.info(f"@831 {LOG_ID} {fp_name.upper()} - not supported address")
            continue
        else:
            logger.info(
                f"@831 {LOG_ID} PU zone: {avail_pu_zone}, DE zone: {avail_de_zone}"
            )

        _rules = []
        for rule in rules:
            if rule.pu_zone in avail_pu_zone and rule.de_zone in avail_de_zone:
                _rules.append(rule)
        rules = _rules

        if not rules:
            logger.info(f"@831 {LOG_ID} {fp_name.upper()} - not supported address")
            continue

        """
            rule_type_03

            Greater of 1) or 2)
            1) 'Basic Charge' + (Booking Qty of the matching 'Charge UOM' x 'Per UOM Charge')
            2) 'Basic Charge' + ((Length in meters x width in meters x height in meters x 'M3 to KG Factor) x 'Per UOM Charge')
        """
        rule = rules[0]
        cost = rule.cost

        if has_pallet:
            price1 = get_booking_lines_count(booking_lines) * cost.per_UOM_charge
        else:
            price1 = 0

            for booking_line in booking_lines:
                price1 += (
                    booking_line.e_qty
                    * booking_line.e_weightPerEach
                    * cost.per_UOM_charge
                )

        price2 = _m3_to_kg(booking_lines, cost.m3_to_kg_factor) * cost.per_UOM_charge
        price0 = price1 if price1 > price2 else price2
        price0 += cost.basic_charge
        net_price = price0 if price0 > cost.min_charge else cost.min_charge

        logger.info(
            f"{LOG_ID} Final cost: {cost} ({cost.basic_charge}, {cost.min_charge}, {cost.per_UOM_charge}, {cost.m3_to_kg_factor})"
        )
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_timing_code}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
