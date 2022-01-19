import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.common.constants import PALLETS
from api.helpers.cubic import get_cubic_meter

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines, pu_zones, de_zones):
    LOG_ID = "[BIP SENDLE]"  # BUILT-IN PRICING
    pricies = []
    total_weight = 0

    for line in booking_lines:
        total_weight += (
            line.e_qty * _get_weight_amount(line.e_weightUOM) * line.e_weightPerEach
        )

        if _get_dim_amount(line.e_dimUOM) * line.e_dimLength > 1.2:
            raise Exception(
                f"{LOG_ID} Exceed max length(1.2m): {_get_dim_amount(line.e_dimUOM) * line.e_dimLength}"
            )

        if _get_dim_amount(line.e_dimUOM) * line.e_dimLength > 1.2:
            raise Exception(
                f"{LOG_ID} Exceed max width(1.2m): {_get_dim_amount(line.e_dimUOM) * line.e_dimLength}"
            )

        if _get_dim_amount(line.e_dimUOM) * line.e_dimLength > 1.2:
            raise Exception(
                f"{LOG_ID} Exceed max height(1.2m): {_get_dim_amount(line.e_dimUOM) * line.e_dimLength}"
            )

    if total_weight > 25:
        raise Exception(f"{LOG_ID} Exceed max weight(25kg): {total_weight}")

    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]
    pu_zone = get_zone_code(booking.pu_Address_PostalCode, fp, pu_zones)
    de_zone = get_zone_code(booking.de_To_Address_PostalCode, fp, de_zones)

    if not pu_zone or not de_zone:
        raise Exception(
            f"Not supported postal_code. [PU: {booking.pu_Address_PostalCode}({pu_zone}), DE: {booking.de_To_Address_PostalCode}({de_zone})]"
        )

    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {service_type.upper()}")

        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id,
            service_type=service_type,
            pu_zone=pu_zone,
            de_zone=de_zone,
        ).order_by("id")
        logger.info(
            f"{LOG_ID} Address filtered: {rules.count()}, PU, DE zone: {pu_zone}, {de_zone}"
        )

        if not rules:
            logger.info(f"{LOG_ID} {fp_name.upper()} - not supported address")
            continue

        rules = weight_filter(booking_lines, rules, fp)
        logger.info(f"{LOG_ID} Weight filtered: {rules.count()}")

        if not rules:
            logger.info(f"{LOG_ID} {fp_name.upper()} - weight exceeded")
            continue

        rules = volume_filter(booking_lines, rules, fp)
        logger.info(f"{LOG_ID} Volume filtered: {rules.count()}")

        if not rules:
            logger.info(f"{LOG_ID} {fp_name.upper()} - volumn exceeded")
            continue

        cost = rules[0].cost
        price = {
            "netPrice": cost.basic_charge,
            "totalTaxes": 0,
            "serviceName": f"{rules[0].service_timing_code}",
            "etd": rules[0].etd.fp_delivery_time_description,
        }
        pricies.append(price)

    return pricies
