from api.models import DME_SMS_Templates
from api.outputs.sms import send_sms


def send_status_update_sms(phone_number, sender, bookingNo, trackingNo, category, eta, status_url):
    if category == 'On Board for Delivery':
        template = DME_SMS_Templates.objects.get(smsName="Status Update - On Board for Delivery")
    elif category == 'Complete':
        template = DME_SMS_Templates.objects.get(smsName="Status Update - Delivered")

    smsMessage = template.smsMessage
    message = smsMessage.format(
        USERNAME=sender,
        BOOKING_NO=bookingNo,
        TRACKING_NO=trackingNo,
        ETA=eta,
        TRACKING_URL=status_url,
    )

    send_sms(phone_number, message)
