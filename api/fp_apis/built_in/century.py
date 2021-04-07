import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *

logger = logging.getLogger("dme_api")


def get_pricing(fp_name, booking, booking_lines):
    LOG_ID = "[BIP CENTURY]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]

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
            rule_type_01

            Booking Qty of the Matching 'Charge UOM' x 'Per UOM Charge'
        """
        logger.info(f"{LOG_ID} {fp_name.upper()} - filtered rules - {rules}")
        cost = (
            FP_costs.objects.filter(pk__in=[rule.cost_id for rule in rules])
            .order_by("per_UOM_charge")
            .first()
        )
        net_price = cost.per_UOM_charge

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
