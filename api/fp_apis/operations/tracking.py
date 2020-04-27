import logging
from datetime import datetime

from django.conf import settings

from api.models import *
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    get_status_category_from_status,
)

logger = logging.getLogger("dme_api")


def _extract(fp_name, consignmentStatus):
    if fp_name.lower() == "startrack":
        b_status_API = consignmentStatus["status"]
        event_time = None
        status_desc = ""
    elif fp_name.lower() in ["tnt"]:
        b_status_API = consignmentStatus["status"][0]
        status_desc = consignmentStatus["statusDescription"][0]
        event_time = consignmentStatus["statusDate"][0]
        event_time = str(datetime.strptime(event_time, "%d/%m/%Y"))
    elif fp_name.lower() in ["hunter"]:
        b_status_API = consignmentStatus["status"]
        status_desc = consignmentStatus["description"]
        event_time = consignmentStatus["statusUpdate"]
        event_time = str(datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%S"))
    elif fp_name.lower() == "sendle":

        b_status_API = consignmentStatus["status"]
        status_desc = consignmentStatus["statusDescription"]
        event_time = consignmentStatus["statusUpdate"]
        event_time = str(datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ"))
    else:
        event_time = None

    return b_status_API, event_time, status_desc


def _get_actual_timestamp(fp_name, consignmentStatuses, type):
    if fp_name in ["tnt", "hunter", "sendle"]:
        for consignmentStatus in consignmentStatuses:
            b_status_API, status_desc, event_time = _extract(fp_name, consignmentStatus)

            b_status = get_dme_status_from_fp_status(fp_name, b_status_API)
            status_category = get_status_category_from_status(b_status)

            if status_category == "Transit" and type == "pickup":
                return event_time
            elif status_category == "Complete" and type == "delivery":
                return event_time

    return None


def update_booking_with_tracking_result(request, booking, fp_name, consignmentStatuses):
    # Get actual_pickup_timestamp
    if not booking.s_20_Actual_Pickup_TimeStamp:
        result = _get_actual_timestamp(fp_name.lower(), consignmentStatuses, "pickup")

        if result:
            booking.s_20_Actual_Pickup_TimeStamp = result

    # Get actual_delivery_timestamp
    if not booking.s_21_Actual_Delivery_TimeStamp:
        result = _get_actual_timestamp(fp_name.lower(), consignmentStatuses, "delivery")

        if result:
            booking.s_21_Actual_Delivery_TimeStamp = result

    # Update booking's latest status
    if fp_name.lower() == "tnt":
        last_consignmentStatus = consignmentStatuses[0]
    else:
        last_consignmentStatus = consignmentStatuses[len(consignmentStatuses) - 1]

    b_status_API, status_desc, event_time = _extract(
        fp_name.lower(), last_consignmentStatus
    )
    booking.b_status_API = b_status_API
    booking.b_status = get_dme_status_from_fp_status(fp_name, b_status_API, booking)
    booking.b_booking_Notes = status_desc
    booking.save()
    status_history.create(booking, booking.b_status, request.user.username, event_time)
