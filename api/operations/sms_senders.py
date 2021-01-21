from api.models import DME_SMS_Templates
from api.outputs.sms import send_sms


def send_status_update_sms(phone_number, bookingNo, status, sender, status_url):
    template = DME_SMS_Templates.objects.get(smsName="Status Update")
    smsMessage = template.smsMessage
    message = smsMessage.format(
        USERNAME=sender,
        BOOKIGNO=bookingNo,
        STATUS=status,
        STATUS_URL=status_url,
    )
    send_sms(phone_number, message)
