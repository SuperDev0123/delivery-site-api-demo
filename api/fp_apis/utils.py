import logging
from datetime import datetime

from django.conf import settings

from api.models import *
from api.common import ratio
from .constants import FP_UOM

logger = logging.getLogger("dme_api")


def _convert_UOM(value, uom, type, fp_name):
    converted_value = value * ratio.get_ratio(uom, FP_UOM[fp_name][type], type)
    return round(converted_value, 2)


def gen_consignment_num(booking_visual_id, prefix_len, digit_len):
    limiter = "1"

    for i in range(digit_len):
        limiter += "0"

    limiter = int(limiter)

    prefix_index = int(booking_visual_id / limiter) + 1
    prefix = chr(int((prefix_index - 1) / 26) + 65) + chr(
        ((prefix_index - 1) % 26) + 65
    )

    return prefix + str(booking_visual_id)[-digit_len:].zfill(digit_len)


def get_dme_status_from_fp_status(fp_name, booking):
    try:
        status_info = Dme_utl_fp_statuses.objects.get(
            fp_name__iexact=fp_name, fp_lookup_status=booking.b_status_API
        )
        return status_info.dme_status
    except Dme_utl_fp_statuses.DoesNotExist:
        booking.b_errorCapture = f"New FP status: {booking.b_status_API}"
        booking.save()
        return None


def get_account_code_key(booking, fp_name):
    from .payload_builder import ACCOUNT_CODES

    # Exceptional case for Bunnings
    if (
        "SWYTEMPBUN" in booking.fk_client_warehouse.client_warehouse_code
        and fp_name.lower() == "hunter"
    ):
        if booking.pu_Address_State == "QLD":
            return "live_bunnings_0"
        elif booking.pu_Address_State == "NSW":
            return "live_bunnings_1"
        else:
            booking.b_errorCapture = f"Not supported State"
            booking.save()
            return None

    if fp_name.lower() not in ACCOUNT_CODES:
        booking.b_errorCapture = f"Not supported FP"
        booking.save()
        return None
    elif booking.api_booking_quote:
        account_code = booking.api_booking_quote.account_code
        account_code_key = None

        for key in ACCOUNT_CODES[fp_name.lower()]:
            if ACCOUNT_CODES[fp_name.lower()][key] == account_code:
                account_code_key = key
                return account_code_key

        if not account_code_key:
            booking.b_errorCapture = f"Not supported ACCOUNT CODE"
            booking.save()
            return None
    elif not booking.api_booking_quote:
        return "live_0"


def _get_etd(pricing):
    fp = Fp_freight_providers.objects.get(
        fp_company_name__iexact=pricing.fk_freight_provider_id
    )

    if fp.fp_company_name.lower() == "tnt":
        return pricing.etd * 24

    try:
        etd = FP_Service_ETDs.objects.get(
            freight_provider_id=fp.id,
            fp_delivery_time_description=pricing.etd,
            fp_delivery_service_code=pricing.service_name,
        )
        return etd.fp_03_delivery_hours
    except Exception as e:
        logger.error(
            f"#810 Missing ETD - {fp.fp_company_name}({fp.id}), {pricing.service_name}, {pricing.etd}"
        )
        return None


def _is_deliverable_price(pricing, booking):
    if booking.pu_PickUp_By_Date and booking.de_Deliver_By_Date:
        timeDelta = booking.de_Deliver_By_Date - booking.puPickUpAvailFrom_Date
        delta_min = 0

        if booking.de_Deliver_By_Hours:
            delta_min += booking.de_Deliver_By_Hours * 60
        if booking.de_Deliver_By_Minutes:
            delta_min += booking.de_Deliver_By_Minutes
        if booking.pu_PickUp_By_Time_Hours:
            delta_min -= booking.pu_PickUp_By_Time_Hours * 60
        if booking.pu_PickUp_By_Time_Minutes:
            delta_min -= pu_PickUp_By_Time_Minutes

        delta_min = timeDelta.total_seconds() / 60 + delta_min
        eta = _get_etd(pricing)

        if not eta:
            return False
        elif float(delta_min) > float(eta) * 60:
            return True
    else:
        return False


# ######################## #
#        Lowest ($$$)      #
# ######################## #
def _get_lowest_price(pricings):
    lowest_pricing = {}
    for pricing in pricings:
        if not lowest_pricing:
            lowest_pricing["pricing"] = pricing
        elif (
            lowest_pricing
            and pricing.fee
            and float(lowest_pricing["pricing"].fee) > float(pricing.fee)
        ):
            lowest_pricing["pricing"] = pricing

    return lowest_pricing


def auto_select_pricing(booking, pricings):
    if len(pricings) == 0:
        booking.b_errorCapture = "No Freight Provider is available"
        booking.save()
        return None

    non_air_freight_pricings = []
    for pricing in pricings:
        if not pricing.service_name or (
            pricing.service_name and pricing.service_name != "Air Freight"
        ):
            non_air_freight_pricings.append(pricing)

    # Check booking.pu_PickUp_By_Date and booking.de_Deliver_By_Date and Pricings etd
    deliverable_pricings = []
    for pricing in non_air_freight_pricings:
        if _is_deliverable_price(pricing, booking):
            deliverable_pricings.append(pricing)

    filtered_pricing = {}
    if deliverable_pricings:
        filtered_pricing = _get_lowest_price(deliverable_pricings)
    elif non_air_freight_pricings:
        filtered_pricing = _get_lowest_price(non_air_freight_pricings)

    if filtered_pricing:
        logger.error(f"#854 Filtered Pricing - {filtered_pricing}")
        booking.api_booking_quote = filtered_pricing["pricing"]
        booking.vx_freight_provider = filtered_pricing["pricing"].fk_freight_provider_id
        booking.vx_account_code = filtered_pricing["pricing"].account_code
        booking.vx_serviceName = filtered_pricing["pricing"].service_name
        booking.inv_cost_actual = filtered_pricing["pricing"].fee
        booking.inv_cost_quoted = filtered_pricing["pricing"].client_mu_1_minimum_values

        fp = Fp_freight_providers.objects.get(
            fp_company_name__iexact=filtered_pricing["pricing"].fk_freight_provider_id
        )

        if fp and fp.service_cutoff_time:
            booking.s_02_Booking_Cutoff_Time = fp.service_cutoff_time
        else:
            booking.s_02_Booking_Cutoff_Time = "12:00:00"

        booking.save()
        return True
    else:
        logger.error("#855 - Could not find proper pricing")
        return False
