import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *
from api.clients.operations.index import get_client

logger = logging.getLogger(__name__)


def get_pricing(fp_name, booking, booking_lines):
    LOG_ID = "[ATC PRICING]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]

    try:
        client = booking.get_client()
    except:
        client = get_client(user=None, kf_client_id=booking["kf_client_id"])

    logger.info(
        f"@830 {LOG_ID} Booking: {booking.b_bookingID_Visual}, Client: {client.company_name}"
    )

    pricies = []
    for service_type in service_types:
        logger.info(f"@830 {LOG_ID} {fp_name.upper()}, {service_type.upper()}")
        rules = FP_pricing_rules.objects.filter(
            freight_provider_id=fp.id,
            service_timing_code__iexact=service_type,
            client=client,
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
        rule = rules.filter(cost_id=cost.id).first()
        price = {
            "netPrice": net_price,
            "totalTaxes": 0,
            "serviceName": f"{rule.service_timing_code}",
            "serviceType": service_type,
            "etd": rule.etd.fp_delivery_time_description,
            "vehicle": rule.vehicle.pk,
        }
        pricies.append(price)

    return pricies
