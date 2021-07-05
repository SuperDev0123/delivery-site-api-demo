import logging
from datetime import datetime

from django.conf import settings

from api.models import *
from api.common import status_history
from api.common.common_times import convert_to_UTC_tz
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    get_status_category_from_status,
)

logger = logging.getLogger(__name__)


def _extract(fp_name, consignmentStatus):
    if fp_name.lower() == "startrack":
        b_status_API = consignmentStatus["status"]
        event_time = None
        status_desc = ""
    elif fp_name.lower() in ["tnt"]:
        b_status_API = consignmentStatus["status"][0]
        status_desc = consignmentStatus["statusDescription"][0]
        event_time = consignmentStatus["statusDate"][0]
        event_time = datetime.strptime(event_time, "%d/%m/%Y")
        event_time = str(convert_to_UTC_tz(event_time))
    elif fp_name.lower() in ["hunter", "sendle", "allied"]:
        b_status_API = consignmentStatus["status"]
        status_desc = consignmentStatus["statusDescription"]
        event_time = consignmentStatus["statusUpdate"]
        event_time = datetime.strptime(event_time[:19], "%Y-%m-%dT%H:%M:%S")
        event_time = str(convert_to_UTC_tz(event_time))
    else:
        event_time = None

    return b_status_API, status_desc, event_time


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
    if booking.z_lock_status:
        msg = f"#380 [TRACKING] Locked Booking: {booking.b_bookingID_Visual}({fp_name})"
        logger.info(msg)
        return True

    if not consignmentStatuses:
        msg = f"#381 [TRACKING] No statuses: {booking.b_bookingID_Visual}({fp_name})"
        logger.info(msg)
        return False

    # Allied
    _consignmentStatuses = consignmentStatuses
    if fp_name.lower() == "allied":
        # Sort by timestamp
        _consignmentStatuses = sorted(
            consignmentStatuses, key=lambda x: x["statusUpdate"]
        )

        # Check partial delivered
        has_delivered_status = False
        last_consignmentStatus = _consignmentStatuses[len(_consignmentStatuses) - 1]

        for _consignmentStatus in _consignmentStatuses:
            if _consignmentStatus["status"] == "DEL":
                has_delivered_status = True
                break

        if has_delivered_status and last_consignmentStatus["status"] != "DEL":
            _consignmentStatuses.append(
                {
                    "status": "PARTDEL",
                    "statusDescription": "Partially Delivered",
                    "statusUpdate": last_consignmentStatus["statusUpdate"],
                }
            )

    # Get actual_pickup_timestamp
    if not booking.s_20_Actual_Pickup_TimeStamp:
        result = _get_actual_timestamp(fp_name.lower(), _consignmentStatuses, "pickup")

        if result:
            booking.s_20_Actual_Pickup_TimeStamp = result

    # Get actual_delivery_timestamp
    if not booking.s_21_Actual_Delivery_TimeStamp:
        result = _get_actual_timestamp(
            fp_name.lower(), _consignmentStatuses, "delivery"
        )

        if result:
            booking.s_21_Actual_Delivery_TimeStamp = result
            booking.delivery_booking = result[:10]

    # Update booking's latest status
    if fp_name.lower() == "startrack":
        last_consignmentStatus = _consignmentStatuses[0]
    else:
        last_consignmentStatus = _consignmentStatuses[len(_consignmentStatuses) - 1]

    b_status_API, status_desc, event_time = _extract(
        fp_name.lower(), last_consignmentStatus
    )
    booking.b_status_API = b_status_API
    status_from_fp = get_dme_status_from_fp_status(fp_name, b_status_API, booking)
    status_history.create(booking, status_from_fp, request.user.username, event_time)
    booking.b_status = status_from_fp
    # booking.b_booking_Notes = status_desc
    booking.save()

    msg = f"#381 [TRACKING] Success: {booking.b_bookingID_Visual}({fp_name})"
    logger.info(msg)
    return True
