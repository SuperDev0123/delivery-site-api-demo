import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.common.ratio import _m3_to_kg
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *

logger = logging.getLogger("dme_api")


def get_pricing(fp_name, booking):
    LOG_ID = "[BIP TOLL]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_deleted=False
    )

    pricies = []
    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")
        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id, service_timing_code__iexact=service_type
        )

        # Address Filter
        rules = address_filter(booking, booking_lines, rules, fp)

        if not rules:
            logger.info(f"@831 {LOG_ID} {fp_name.upper()} - not supported address")
            continue

        logger.info(
            f"{LOG_ID} {fp_name.upper()} - applying size filter... rules cnt: {rules.count()}"
        )
        # Size(dim) Filter
        if fp.rule_type.rule_type_code in ["rule_type_01", "rule_type_02"]:
            rules = dim_filter(booking, booking_lines, rules, fp)

            if not rules:
                continue

        """
            rule_type_03

            Greater of 1) or 2)
            1) 'Basic Charge' + (Booking Qty of the matching 'Charge UOM' x 'Per UOM Charge')
            2) 'Basic Charge' + ((Length in meters x width in meters x height in meters x 'M3 to KG Factor) x 'Per UOM Charge')
        """
        cost = rules.first().cost
        price1 = get_booking_lines_count(booking_lines) * cost.per_UOM_charge
        price2 = _m3_to_kg(booking_lines, cost.m3_to_kg_factor) * cost.per_UOM_charge
        price0 = price1 if price1 > price2 else price2
        price0 += cost.basic_charge
        net_price = price0 if price0 > cost.min_charge else cost.min_charge

        logger.info(f"{LOG_ID} {fp_name.upper()} - final cost - {cost}")
        rule = rules.get(cost_id=cost.id)
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_timing_code}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
