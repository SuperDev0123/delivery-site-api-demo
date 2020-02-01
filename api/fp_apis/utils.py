from django.conf import settings
from api.models import *

from .payload_builder import ACCOUTN_CODES


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
    if not booking.api_booking_quote:
        booking.b_errorCapture = f"Please select a Pricing"
        booking.save()
        return None
    elif fp_name.lower() not in ACCOUTN_CODES:
        booking.b_errorCapture = f"Not supported FP"
        booking.save()
        return None
    else:
        account_code = booking.api_booking_quote.account_code
        account_key = None

        for key in ACCOUTN_CODES[fp_name.lower()]:
            if ACCOUTN_CODES[fp_name.lower()][key] == account_code:
                account_key = key
                return account_key

        if not account_key:
            booking.b_errorCapture = f"Not supported ACCOUNT CODE"
            booking.save()
            return None


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
                print("@100 - ", delta_min)
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
        print("@101 - ")
        print(pricing.etd)
        return None
    else:
        print("@102 - ")
        print("#855 - Could not find proper pricing")
        return None


def _get_etd(pricing):
    if not pricing.etd:
        return None, None

    if pricing.fk_freight_provider_id.lower() == "hunter":
        temp = pricing.etd.lower().split("days")[0]
        min = float(temp.split("-")[0])
        max = float(temp.split("-")[1])
    elif pricing.fk_freight_provider_id.lower() == "sendle":
        min = float(pricing.etd.split(",")[0])
        max = float(pricing.etd.split(",")[1])
    elif pricing.fk_freight_provider_id.lower() == "tnt":
        min = 0
        max = float(pricing.etd.lower().split("days")[0])

    return min * 24 * 60, max * 24 * 60
