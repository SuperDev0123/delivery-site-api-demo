from django.conf import settings
from api.models import *

from .payload_builder import ACCOUTN_CODES


def get_dme_status_from_fp_status(fp_name, booking):
    try:
        status_info = Dme_utl_fp_statuses.objects.get(
            fp_name__iexact=fp_name, fp_original_status=booking.b_status_API
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
