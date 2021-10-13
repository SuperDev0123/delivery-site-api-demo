import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.helpers.cubic import get_cubic_meter

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines):
    LOG_ID = "[BIP TNT]"  # BUILT-IN PRICING
    pricies = []

    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    pu_zone = get_zone_code(booking.pu_Address_PostalCode, fp)
    de_zone = get_zone_code(booking.de_To_Address_PostalCode, fp)

    if not pu_zone or not de_zone:
        raise Exception(
            f"Not supported postal_code. [PU: {booking.pu_Address_PostalCode}({pu_zone}), DE: {booking.de_To_Address_PostalCode}({de_zone})]"
        )

    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")

        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id,
            service_type=service_type,
            pu_zone=pu_zone,
            de_zone=de_zone,
        ).order_by("id")

        # Weight Filter
        logger.info(f"{LOG_ID} Applying weight filter... rules cnt: {rules.count()}")
        rules = weight_filter(booking_lines, rules, fp)
        # logger.info(f"{LOG_ID} Filtered rules - {rules}")
        if not rules:
            continue

        """
            rule_type_02

            Booking Qty of the Matching 'Charge UOM' x 'Per UOM Charge
        """
        cost = rules.first().cost
        net_price = cost.basic_charge or 0
        m3_to_kg_factor = 250
        dead_weight, cubic_weight = 0, 0

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
        net_price += float(cost.per_UOM_charge or 0) * chargable_weight

        if cost.min_charge and net_price < cost.min_charge:
            net_price = cost.min_charge

        logger.info(f"{LOG_ID} Final cost - {cost}")
        rule = rules.get(cost_id=cost.id)
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_type}",
            "etd": rule.etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
