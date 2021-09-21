import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines):
    LOG_ID = "[BIP NORTHLINE]"  # BUILT-IN PRICING
    pricies = []

    # if booking.de_To_AddressType and booking.de_To_AddressType.lower() == "residential":
    #     logger.info(f"@830 {LOG_ID} Not available for `Residential`")
    #     return pricies

    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")
        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id, service_timing_code__iexact=service_type
        ).order_by("id")

        # Address Filter
        rules = address_filter(booking, booking_lines, rules, fp)

        if not rules:
            logger.info(f"@831 {LOG_ID} {fp_name.upper()} - not supported address")
            continue

        logger.info(
            f"{LOG_ID} {fp_name.upper()} - applying weight filter... rules cnt: {rules.count()}"
        )
        # Weight Filter
        if fp.rule_type.rule_type_code in ["rule_type_01", "rule_type_02"]:
            rules = weight_filter(booking_lines, rules, fp)

            if not rules:
                continue

        """
            rule_type_02

            Booking Qty of the Matching 'Charge UOM' x 'Per UOM Charge
        """
        logger.info(f"{LOG_ID} {fp_name.upper()} - filtered rules - {rules}")
        rules = weight_filter(booking_lines, rules, fp)
        cost = rules.first().cost
        net_price = cost.basic_charge
        m3_to_kg_factor = 330
        dead_weight, cubic_weight = 0

        for item in booking_lines:
            dead_weight += (
                item.e_weightPerEach * _get_weight_amount(item.e_weightUOM) * item.e_qty
            )
            cubic_weight += (
                get_cubic_meter(
                    item.e_dimLength,
                    item.e_dimWidth,
                    item.e_dimHeight,
                    item.e_dimUOM,
                    item.e_qty,
                )
                * m3_to_kg_factor
            )

        chargable_weight = dead_weight if dead_weight > cubic_weight else cubic_weight
        net_price += float(cost.per_UOM_charge) * chargable_weight

        if net_price < cost.min_charge:
            net_price = cost.min_charge

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
