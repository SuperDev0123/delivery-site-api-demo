import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.common.ratio import _m3_to_kg
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines, pu_zones, de_zones):
    LOG_ID = "[BIP TOLL]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]

    pricies = []
    fp_rules = FP_pricing_rules.objects.filter(freight_provider_id=fp.id)
    if not fp_rules: 
        return pricies
    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")
        # rules = FP_pricing_rules.objects.filter(
        #     freight_provider_id=fp.id, service_timing_code__iexact=service_type
        # )
        rules = []
        for fp_rule in fp_rules:
            if (fp_rule.service_timing_code.lower() == service_type.lower()):
                rules.append(fp_rule)
        # Address Filter
        rules = address_filter(booking, booking_lines, rules, fp, pu_zones, de_zones)

        if not rules:
            logger.info(f"@831 {LOG_ID} {fp_name.upper()} - not supported address")
            continue

        logger.info(
            f"{LOG_ID} {fp_name.upper()} - applying size filter... rules cnt: {len(rules)}"
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
        cost = rules[0].cost
        price1 = get_booking_lines_count(booking_lines) * cost.per_UOM_charge
        price2 = _m3_to_kg(booking_lines, cost.m3_to_kg_factor) * cost.per_UOM_charge
        price0 = price1 if price1 > price2 else price2
        price0 += cost.basic_charge
        net_price = price0 if price0 > cost.min_charge else cost.min_charge

        logger.info(f"{LOG_ID} {fp_name.upper()} - final cost - {cost}")
        rule = list(filter(lambda rule: rule.cost_id == cost.id, rules))[0]
        if not rule.etd:
            continue
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_timing_code}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
