from datetime import datetime, date, timedelta

from api.models import Dme_status_history
from api.outputs import tempo, automation

# Create new status_history for Booking
def create(booking, status, username, event_timestamp=None):
    if not booking.z_lock_status:
        status_histories = Dme_status_history.objects.filter(
            fk_booking_id=booking.pk_booking_id
        ).order_by("-id")

        if status_histories.exists():
            last_status_history = status_histories.first()
        else:
            last_status_history = None

        if not last_status_history or (
            last_status_history and last_status_history.status_last != status
        ):
            dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
            dme_status_history.status_old = booking.b_status
            dme_status_history.notes = f"{str(booking.b_status)} ---> {str(status)}"
            dme_status_history.status_last = status
            dme_status_history.event_time_stamp = (
                event_timestamp if event_timestamp else datetime.now()
            )
            dme_status_history.recipient_name = ""
            dme_status_history.status_update_via = "Django"
            dme_status_history.z_createdByAccount = username
            dme_status_history.save()

            automation.send_sms( dme_status_history.notes, booking.pu_Phone_Mobile)
            automation.send_sms( dme_status_history.notes, booking.de_to_Phone_Mobile)

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
