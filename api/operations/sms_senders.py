import logging

from api.models import DME_SMS_Templates
from api.outputs.sms import send_sms

logger = logging.getLogger(__name__)


def send_status_update_sms(
    phone_number, sender, client, bookingNo, trackingNo, category, eta, status_url
):
    LOG_ID = "[STATUS UPDATE SMS]"

    if not category in ["Transit", "On Board for Delivery", "Complete"]:
        return

    logger.info(
        f"{LOG_ID} BookingID: {bookingNo}, PhoneNumber: {phone_number}, Category: {category}"
    )

    if category == "Transit":
        template = DME_SMS_Templates.objects.get(
            smsName="Status Update - Transit"
        )
    elif category == "On Board for Delivery":
        template = DME_SMS_Templates.objects.get(
            smsName="Status Update - On Board for Delivery"
        )
    elif category == "Complete":
        template = DME_SMS_Templates.objects.get(smsName="Status Update - Delivered")

    if template:
        smsMessage = template.smsMessage
        message = smsMessage.format(
            USERNAME=sender,
            CLIENT_NAME=client,
            BOOKING_NO=bookingNo,
            TRACKING_NO=trackingNo,
            ETA=eta,
            TRACKING_URL=status_url,
        )

        print('mmmmmmmmmmmmm\n', message)
        # send_sms(phone_number, message)
