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
    if "SWYTEMPBUN" in booking.fk_client_warehouse.client_warehouse_code:
        if booking.pu_Address_State == "QLD":
            return ACCOUTN_CODES[fp_name.lower()]["live_bunnings_0"]
        elif booking.pu_Address_State == "NSW":
            return ACCOUTN_CODES[fp_name.lower()]["live_bunnings_1"]
        else:
            booking.b_errorCapture = f"Not supported State"
            booking.save()
            return None

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
        account_code_key = None

        for key in ACCOUTN_CODES[fp_name.lower()]:
            if ACCOUTN_CODES[fp_name.lower()][key] == account_code:
                account_key = key
                return account_code_key

        if not account_key:
            booking.b_errorCapture = f"Not supported ACCOUNT CODE"
            booking.save()
            return None
