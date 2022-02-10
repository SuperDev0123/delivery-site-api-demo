import math, logging
from datetime import datetime, date

from django.conf import settings

from api.models import Dme_status_history, DME_clients
from api.outputs import tempo
from api.operations.sms_senders import send_status_update_sms
from api.operations.email_senders import send_status_update_email
from api.helpers.phone import is_mobile, format_mobile
from api.operations.packing.booking import scanned_repack as booking_scanned_repack
from api.common import common_times as dme_time_lib

logger = logging.getLogger(__name__)


def notify_user_via_email_sms(booking, category_new, category_old, username):
    from api.helpers.etd import get_etd

    # JasonL is deactivated(2022-02-10) - "461162D2-90C7-BF4E-A905-000000000004"
    # JasonL and Plum & BSD
    if not booking.kf_client_id in [
        "1af6bcd2-6148-11eb-ae93-0242ac130002",
        "9e72da0f-77c3-4355-a5ce-70611ffd0bc8",
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
            dme_time_lib.next_business_day(
                dme_time_lib.convert_to_AU_SYDNEY_tz(booking.puPickUpAvailFrom_Date),
                etd,
                booking.vx_freight_provider,
            ).strftime("%d/%m/%Y")
            if etd and booking.puPickUpAvailFrom_Date
            else ""
        )

        eta_etd = f"{eta}({etd} days)" if eta else ""

        pu_name = booking.pu_Contact_F_L_Name or booking.puCompany
        de_name = booking.de_to_Contact_F_LName or booking.deToCompanyName
        de_company = booking.deToCompanyName
        de_address = f"{booking.de_To_Address_Street_1}{f' {booking.de_To_Address_Street_2}' or ''} {booking.de_To_Address_Suburb} {booking.de_To_Address_State} {booking.de_To_Address_Country} {booking.de_To_Address_PostalCode}"
        delivered_time = (
            booking.s_21_Actual_Delivery_TimeStamp.strftime("%d/%m/%Y %H:%M")
            if booking.s_21_Actual_Delivery_TimeStamp
            else ""
        )

        email_sent = False
        if settings.ENV == "prod":
            try:
                client = DME_clients.objects.get(dme_account_num=booking.kf_client_id)
            except Exception as e:
                logger.info(f"Get client error: {str(e)}")
                client = None

            if client and client.status_send_flag:
                if client.status_email:
                    # Send email to client too -- TEST USAGE
                    send_status_update_email(
                        booking,
                        category_new,
                        eta_etd,
                        username,
                        url,
                        client.status_email,
                    )
                    email_sent = True

                if client.status_phone and is_mobile(client.status_phone):
                    # TEST USAGE --- Send SMS to Plum agent
                    send_status_update_sms(
                        format_mobile(client.status_phone),
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

                # # TEST USAGE --- Send SMS to Stephen (A week period)
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

        if not email_sent:
            send_status_update_email(booking, category_new, eta_etd, username, url)

        if booking.de_to_Phone_Main and is_mobile(booking.de_to_Phone_Main):
            send_status_update_sms(
                format_mobile(booking.de_to_Phone_Main),
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

        if booking.de_to_Phone_Mobile and is_mobile(booking.de_to_Phone_Mobile):
            send_status_update_sms(
                format_mobile(booking.de_to_Phone_Mobile),
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


def notify_user_via_api(booking, event_timestamp):
    tempo.push_via_api(booking, event_timestamp)


def post_new_status(booking, dme_status_history, new_status, event_timestamp, username):
    from api.fp_apis.utils import get_status_category_from_status

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

    booking.b_status_category = category_new
    booking.save()
    booking.refresh_from_db()

    notify_user_via_email_sms(booking, category_new, category_old, username)
    notify_user_via_api(booking, event_timestamp)


# Create new status_history for Booking
def create(booking, new_status, username, event_timestamp=None):
    if booking.z_lock_status:
        logger.info(f"@699 Booking({booking.b_bookingID_Visual}) is locked!")
        return

    status_histories = Dme_status_history.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).order_by("-id")

    if status_histories.exists():
        last_status_history = status_histories.first()
    else:
        last_status_history = None

    old_status = booking.b_status
    booking.b_status = new_status
    booking.save()

    if not last_status_history or (
        last_status_history
        and new_status
        and last_status_history.status_last != new_status
    ):
        dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
        notes = f"{str(old_status)} ---> {str(new_status)}"
        logger.info(f"@700 New Status! {booking.b_bookingID_Visual}({notes})")

        dme_status_history.status_old = old_status
        dme_status_history.notes = notes
        dme_status_history.status_last = new_status
        dme_status_history.event_time_stamp = event_timestamp or datetime.now()
        dme_status_history.recipient_name = ""
        dme_status_history.status_update_via = "Django"
        dme_status_history.z_createdByAccount = username
        dme_status_history.save()

        post_new_status(
            booking, dme_status_history, new_status, event_timestamp, username
        )

        if new_status == "Booked":
            booking_scanned_repack(booking)


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
