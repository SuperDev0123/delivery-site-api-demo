import logging
import traceback

from api.models import Fp_freight_providers, Booking_lines, FP_pricing_rules, FP_costs
from api.common.ratio import _get_dim_amount, _get_weight_amount
from api.fp_apis.constants import BUILT_IN_PRICINGS
from api.fp_apis.built_in.operations import *

logger = logging.getLogger("dme_api")


def has_oversize_pallet(fp_name, booking_lines):
    """
    standard pallet
        size: 1.2 x 1.2 x 1.4 meter
        weight: 500 kg

    oversize pallet
        size: 1.2 x 1.2 x 2.1 meter
        weight: 1000 kg
    """

    LOG_ID = "[has_oversize_pallet]"

    standard_width = 1.2
    standard_length = 1.2
    standard_height = 1.4
    standard_weight = 500

    oversize_width = 1.2
    oversize_length = 1.2
    oversize_height = 2.1
    oversize_weight = 1000

    size_types = []
    for item in booking_lines:
        width = _get_dim_amount(item.e_dimUOM) * item.e_dimWidth
        length = _get_dim_amount(item.e_dimUOM) * item.e_dimLength
        height = _get_dim_amount(item.e_dimUOM) * item.e_dimHeight
        weight = _get_weight_amount(item.e_weightUOM) * item.e_weightPerEach

        if (
            width < standard_width
            and length < standard_length
            and height < standard_height
            and weight < standard_weight
        ):
            size_type = "STANDARD"
        elif (
            width < oversize_width
            and length < oversize_length
            and height < oversize_height
            and weight < oversize_weight
        ):
            size_type = "OVERSIZE"
        else:
            message = f"@731 {LOG_ID} {fp_name.upper()} Booking has a line that size/weight is not supported."
            logger.info(message)
            raise Exception(message)

        if not size_type in size_types:
            size_types.append(size_type)

    if "OVERSIZE" in size_types:
        return True
    else:
        return False


def select_service_type(fp_name, booking_lines):
    LOG_ID = "[select_service_type]"
    service_types = BUILT_IN_PRICINGS[fp_name]["service_types"]

    # Check if Booking has only `Carton`s or `Pallet`s
    e_type_of_packagings = []
    for booking_line in booking_lines:
        if booking_line.e_type_of_packaging.upper() in ["CTN", "CARTON"]:
            e_type_of_packaging = "carton"
        else:
            e_type_of_packaging = "pallet"

        if not e_type_of_packaging in e_type_of_packagings:
            e_type_of_packagings.append(e_type_of_packaging)

    if len(e_type_of_packagings) == 0 or len(e_type_of_packagings) == 2:
        message = f"@730 {LOG_ID} {fp_name.upper()} Booking has lines packed by different types."
        logger.info(message)
        raise Exception(message)

    if e_type_of_packagings[0] == "carton":
        return service_types[0]  # "Road Express"
    else:
        if not has_oversize_pallet(fp_name, booking_lines):
            return service_types[1]  # "Standard Pallet Rate"
        else:
            return service_types[2]  # "Oversized Pallet Rate"


def get_pricing(fp_name, booking):
    LOG_ID = "[BIP ALLIED]"  # BUILT-IN PRICING
    fp = Fp_freight_providers.objects.get(fp_company_name__iexact=fp_name)
    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id, is_deleted=False
    )

    # Select service_type
    service_type = select_service_type(fp_name, booking_lines)
    logger.info(f"@830 {LOG_ID} {service_type.upper()}")

    # Get pu_zone and de_zone
    pu_zone = get_zone(
        fp=fp,
        state=booking.pu_Address_State,
        postal_code=booking.pu_Address_PostalCode,
        suburb=booking.pu_Address_Suburb,
    )
    de_zone = get_zone(
        fp=fp,
        state=booking.de_To_Address_State,
        postal_code=booking.de_To_Address_PostalCode,
        suburb=booking.de_To_Address_Suburb,
    )
    logger.info(f"@831 {LOG_ID} PU Zone: {pu_zone}, DE Zone: {de_zone}")

    if not pu_zone or not de_zone:
        message = f"@832 {LOG_ID} PU/DE address is not supported."
        logger.info(message)
        raise Exception(message)

    rules = FP_pricing_rules.objects.filter(
        freight_provider_id=fp.id,
        service_type=service_type,
        pu_zone=pu_zone.zone,
        de_zone=de_zone.zone,
    )

    if not rules:
        message = f"@833 {LOG_ID} Does not found matching Rule."
        logger.info(message)
        raise Exception(message)

    cost = rules.first().cost
    message = f"@834 {LOG_ID} RuleID: {rules.first()}, CostID: {cost}"
    logger.info(message)

    if service_type == "Road Express":
        net_price = cost.basic_charge

        for item in booking_lines:
            net_price += float(cost.per_UOM_charge) * item.e_qty

        if net_price < cost.min_charge:
            net_price = cost.min_charge
    else:
        net_price = 0

        for item in booking_lines:
            net_price += float(cost.per_UOM_charge) * item.e_qty

    price = {
        "netPrice": net_price,
        "totalTaxes": 0,
        "serviceName": service_type,
        "etd": 3,
    }

    message = f"@835 {LOG_ID} result: {price}"
    logger.info(message)
    return [price]
