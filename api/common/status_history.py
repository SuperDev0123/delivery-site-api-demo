import logging
from datetime import datetime, date, timedelta

from django.conf import settings

from api.models import Dme_status_history
from api.outputs import tempo
from api.operations.sms_senders import send_status_update_sms
from api.operations.email_senders import send_status_update_email

logger = logging.getLogger(__name__)

# Create new status_history for Booking
def create(booking, status, username, event_timestamp=None):
    if booking.z_lock_status:
        return

    status_histories = Dme_status_history.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).order_by("-id")

    if status_histories.exists():
        last_status_history = status_histories.first()
    else:
        last_status_history = None

    if not last_status_history or (
        last_status_history and status and last_status_history.status_last != status
    ):
        dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
        notes = f"{str(booking.b_status)} ---> {str(status)}"
        logger.info(f"@700 New Status! {booking.b_bookingID_Visual}({notes})")

        dme_status_history.status_old = booking.b_status
        dme_status_history.notes = notes
        dme_status_history.status_last = status
        dme_status_history.event_time_stamp = (
            event_timestamp if event_timestamp else datetime.now()
        )
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = "Django"
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()

        # if (
        #     booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004"
        #     and dme_status_history.status_last == "In Transit"
        #     and dme_status_history.status_old != "In Transit"
        # ):
        #     url = f"http://{settings.WEB_SITE_IP}/status/{booking.b_client_booking_ref_num}/"

        #     if "Email" in booking.de_To_Comm_Delivery_Communicate_Via:
        #         send_status_update_email(booking, notes, username, url)
        #     if "SMS" in booking.de_To_Comm_Delivery_Communicate_Via:
        #         send_status_update_sms(
        #             booking.pu_Phone_Mobile,
        #             booking.b_client_order_num,
        #             notes,
        #             username,
        #             url,
        #         )
        #         send_status_update_sms(
        #             booking.de_to_Phone_Mobile,
        #             booking.b_client_order_num,
        #             notes,
        #             username,
        #             url,
        #         )

        if status.lower() == "delivered":
            if event_timestamp:
                booking.s_21_Actual_Delivery_TimeStamp = event_timestamp
                booking.delivery_booking = event_timestamp[:10]

            booking.z_api_issue_update_flag_500 = 0
            booking.z_lock_status = 1
            booking.save()

    tempo.push_via_api(booking)


# Create new status_history for Bok
def create_4_bok(pk_header_id, status, username, event_timestamp=None):
    status_histories = Dme_status_history.objects.filter(
        fk_booking_id=pk_header_id
    ).order_by("-id")

    if status_histories.exists():
        last_status_history = status_histories.first()
    else:
        last_status_history = None

    if not last_status_history or (
        last_status_history and last_status_history.status_last != status
    ):
        dme_status_history = Dme_status_history(fk_booking_id=pk_header_id)

        if last_status_history:
            dme_status_history.status_old = last_status_history.status_last
            dme_status_history.notes = (
                f"{str(last_status_history.status_last)} ---> {str(status)}"
            )

        dme_status_history.status_last = status
        dme_status_history.event_time_stamp = (
            event_timestamp if event_timestamp else datetime.now()
        )
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = "Django"
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()
