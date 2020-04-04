import logging

from django.conf import settings

from api.models import *
from api.common import ratio
from datetime import datetime

logger = logging.getLogger("dme_api")

FP_UOM = {
    "startrack": {"dim": "cm", "weight": "kg"},
    "hunter": {"dim": "cm", "weight": "kg"},
    "tnt": {"dim": "cm", "weight": "kg"},
    "capital": {"dim": "cm", "weight": "kg"},
    "sendle": {"dim": "cm", "weight": "kg"},
    "fastway": {"dim": "cm", "weight": "kg"},
    "allied": {"dim": "cm", "weight": "kg"},
    "dhl": {"dim": "cm", "weight": "kg"},
}


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


def auto_select(booking, pricings):
    if len(pricings) == 0:
        booking.b_errorCapture = "No Freight Provider is available"
        booking.save()
        return None

    filtered_pricing = {}
    for pricing in pricings:
        if not pricing.service_name or (
            pricing.service_name and pricing.service_name != "Air Freight"
        ):
            etd_min, etd_max = _get_etd(pricing)

            if booking.puPickUpAvailFrom_Date and booking.de_Deliver_By_Date:
                timeDelta = booking.de_Deliver_By_Date - booking.puPickUpAvailFrom_Date
                delta_min = 0

                if booking.pu_PickUp_Avail_Time_Hours:
                    delta_min = booking.pu_PickUp_Avail_Time_Hours * 60
                if booking.pu_PickUp_Avail_Time_Minutes:
                    delta_min += pu_PickUp_Avail_Time_Minutes
                if booking.de_Deliver_By_Hours:
                    delta_min -= booking.de_Deliver_By_Hours * 60
                if booking.de_Deliver_By_Minutes:
                    delta_min -= booking.de_Deliver_By_Minutes

                delta_min = timeDelta.total_seconds() / 60 + delta_min

                if delta_min > etd_max and not filtered_pricing:
                    filtered_pricing["pricing"] = pricing
                    filtered_pricing["etd_max"] = etd_max
                elif (
                    delta_min > etd_max
                    and filtered_pricing
                    and filtered_pricing["pricing"].fee > pricing.fee
                ):
                    filtered_pricing["pricing"] = pricing
                    filtered_pricing["etd_max"] = etd_max
            else:
                if not filtered_pricing:
                    filtered_pricing["pricing"] = pricing
                    filtered_pricing["etd_max"] = etd_max
                elif filtered_pricing and filtered_pricing["pricing"].fee > pricing.fee:
                    filtered_pricing["pricing"] = pricing
                    filtered_pricing["etd_max"] = etd_max

    if filtered_pricing:
        logger.error(f"#854 Filtered Pricing - {filtered_pricing}")
        booking.vx_freight_provider = filtered_pricing["pricing"].fk_freight_provider_id
        booking.vx_account_code = filtered_pricing["pricing"].account_code
        booking.vx_serviceName = filtered_pricing["pricing"].service_name
        booking.api_booking_quote = filtered_pricing["pricing"]

        fp_freight_provider = Fp_freight_providers.objects.filter(fp_company_name=booking.vx_freight_provider).first()

        if ( fp_freight_provider is not None 
            and 
            fp_freight_provider.service_cutoff_time is not None):
            booking.s_02_Booking_Cutoff_Time = fp_freight_provider.service_cutoff_time
        else:
            booking.s_02_Booking_Cutoff_Time = datetime.strptime('12:00:00', '%H:%M:%S').time()

        booking.save()
        return True
    else:
        logger.error("#855 - Could not find proper pricing")
        return False


def _get_etd(pricing):
    min = None
    max = None

    if not pricing.etd:
        return None, None

    if pricing.etd.lower() == "overnight":
        min = 1
        max = 1
    else:
        if pricing.fk_freight_provider_id.lower() == "hunter":
            temp = pricing.etd.lower().split("days")[0]
            min = float(temp.split("-")[0])
            max = float(temp.split("-")[1])
        elif pricing.fk_freight_provider_id.lower() in ["sendle", "century"]:
            min = float(pricing.etd.split(",")[0])
            max = float(pricing.etd.split(",")[1])
        elif pricing.fk_freight_provider_id.lower() in ["tnt", "toll", "camerons"]:
            min = 0
            max = float(pricing.etd.lower().split("days")[0])

    if max:
        return min * 24 * 60, max * 24 * 60
    else:
        return ""
