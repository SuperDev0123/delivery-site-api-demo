from datetime import datetime, date, timedelta

from api.models import Dme_status_history


# Create new status_history
def create(booking, username):
    last_status_history = None
    try:
        last_status_history = (
            Dme_status_history.objects.filter(fk_booking_id=booking.pk_booking_id)
            .order_by("-id")
            .first()
        )
    except:
        last_status_history = None

    if not last_status_history or (
        last_status_history and last_status_history.status_last != booking.status
    ):
        dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
        dme_status_history.status_old = booking.b_status
        dme_status_history.notes = f"{str(booking.b_status)}--->{str(status)}"
        dme_status_history.status_last = status
        dme_status_history.event_time_stamp = datetime.now()
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = ""
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()
