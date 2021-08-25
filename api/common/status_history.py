import math, logging
from datetime import datetime, date, timedelta

from django.conf import settings

from api.models import Dme_status_history
from api.outputs import tempo
from api.operations.sms_senders import send_status_update_sms
from api.operations.email_senders import send_status_update_email

logger = logging.getLogger(__name__)


def notify_user_via_email_sms(booking, category_new, category_old):
    # JasonL and Plum
    if not booking.kf_client_id in [
        "461162D2-90C7-BF4E-A905-000000000004",
        "1af6bcd2-6148-11eb-ae93-0242ac130002",
    ]:
        return

    if (
        category_new
        in [
            "Transit",
            "On Board for Delivery",
            "Complete",
            "Futile",
            "Returned",
        ]
        and category_new != category_old
    ):
        url = f"{settings.WEB_SITE_URL}/status/{booking.b_client_booking_ref_num}/"

        quote = booking.api_booking_quote
        if quote:
            etd, unit = get_etd(quote.etd)
            if unit == "Hours":
                etd = math.ceil(etd / 24)
        else:
            etd, unit = None, None

        eta = (
            (booking.puPickUpAvailFrom_Date + timedelta(days=etd)).strftime("%d/%m/%Y")
            if etd and booking.puPickUpAvailFrom_Date
            else ""
        )

        eta_etd = f"{eta}({etd} days)" if eta else ""

        if booking.de_Email:
            send_status_update_email(booking, category_new, eta_etd, username, url)

        pu_name = booking.pu_Contact_F_L_Name or booking.puCompany
        de_name = booking.de_to_Contact_F_LName or booking.deToCompanyName
        de_company = booking.deToCompanyName
        de_address = f"{booking.de_To_Address_Street_1}{f' {booking.de_To_Address_Street_2}' or ''} {booking.de_To_Address_Suburb} {booking.de_To_Address_State} {booking.de_To_Address_Country} {booking.de_To_Address_PostalCode}"
        delivered_time = (
            booking.s_21_Actual_Delivery_TimeStamp.strftime("%d/%m/%Y %H:%M")
            if booking.s_21_Actual_Delivery_TimeStamp
            else ""
        )

        if booking.de_to_Phone_Main or booking.de_to_Phone_Mobile:
            send_status_update_sms(
                booking.de_to_Phone_Main or booking.de_to_Phone_Mobile,
                de_name,
                booking.b_client_name,
                booking.b_bookingID_Visual,
                booking.v_FPBookingNumber,
                category_new,
                eta,
                url,
                de_company,
                de_address,
                delivered_time,
            )

        if (
            settings.ENV == "prod"
            and booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000004"
        ):
            # Send SMS to Plum agent
            send_status_update_sms(
                "0411608093",
                de_name,
                booking.b_client_name,
                booking.b_bookingID_Visual,
                booking.v_FPBookingNumber,
                category_new,
                eta,
                url,
                de_company,
                de_address,
                delivered_time,
            )
            # send_status_update_sms(
            #     booking.pu_Phone_Main,
            #     pu_name,
            #     booking.b_bookingID_Visual,
            #     booking.v_FPBookingNumber,
            #     category_new,
            #     eta,
            #     url
            # )

        # Send SMS to Stephen (A week period)
        send_status_update_sms(
            "0499776446",
            de_name,
            booking.b_client_name,
            booking.b_bookingID_Visual,
            booking.v_FPBookingNumber,
            category_new,
            eta,
            url,
            de_company,
            de_address,
            delivered_time,
        )


def notify_user_via_api(booking):
    tempo.push_via_api(booking)


def post_new_status(booking, dme_status_history, new_status):
    category_new = get_status_category_from_status(dme_status_history.status_last)
    category_old = get_status_category_from_status(dme_status_history.status_old)

    if category_new == "Transit" and category_old != "Transit":
        if not booking.b_given_to_transport_date_time:
            booking.b_given_to_transport_date_time = datetime.now()

        if not booking.s_20_Actual_Pickup_TimeStamp:
            booking.s_20_Actual_Pickup_TimeStamp = datetime.now()

    if new_status.lower() == "delivered":
        booking.z_api_issue_update_flag_500 = 0
        booking.z_lock_status = 1

        if event_timestamp:
            booking.s_21_Actual_Delivery_TimeStamp = event_timestamp
            booking.delivery_booking = event_timestamp[:10]

    booking.b_status = new_status
    booking.save()

    notify_user_via_email_sms(booking, category_new, category_old)
    notify_user_via_api(booking)


# Create new status_history for Booking
def create(booking, new_status, username, event_timestamp=None):
    from api.fp_apis.utils import get_status_category_from_status
    from api.helpers.etd import get_etd

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
        last_status_history
        and new_status
        and last_status_history.status_last != new_status
    ):
        dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
        notes = f"{str(booking.b_status)} ---> {str(new_status)}"
        logger.info(f"@700 New Status! {booking.b_bookingID_Visual}({notes})")

        dme_status_history.status_old = booking.b_status
        dme_status_history.notes = notes
        dme_status_history.status_last = new_status
        dme_status_history.event_time_stamp = event_timestamp or datetime.now()
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = "Django"
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()

        post_new_status(booking, dme_status_history, new_status)


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
        dme_status_history.event_time_stamp = event_timestamp or datetime.now()
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = "Django"
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()
