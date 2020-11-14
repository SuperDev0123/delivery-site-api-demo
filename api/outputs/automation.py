import sys, time
import os, base64
from datetime import datetime
from email.utils import COMMASPACE
from django.conf import settings
from api.models import *
from twilio.rest import Client
from django.conf import settings
from api.utils import send_email

ENV = 'production'
if ENV == 'test':
    account_sid = "AC3476f2ed21f2d16213f1ba58614f7c51"
    auth_token  = "670ab2e82cd4a4701fedb36a82579e6d"
else:
    account_sid = settings.TWILIO['APP_SID']
    auth_token = settings.TWILIO['TOKEN']

def send_sms(phone_number, bookingId, status, sender, status_url):
    # html = message

    client = Client(account_sid, auth_token)
    template = DME_SMS_Templates.objects.filter(smsName="Status Update").first()
    smsMessage = template.smsMessage
    message = smsMessage.format(USERNAME=sender, BOOKIGNO=bookingId, STATUS=status, STATUS_URL=status_url)
    if ENV == 'test':
        phone_number = "+17634069539"
        msg = client.messages.create(to="+17634069539", from_="+15005550006",body=message)
    else:
        msg = client.messages.create(to=phone_number,from_=settings.TWILIO['NUMBER'],body=message)
    print('twilio sent msg id', msg.sid)


def send_status_update_email(bookingId, status, sender, status_url):
    # html = message

    booking = Bookings.objects.get(pk=int(bookingId))
    cc_emails = []

    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).order_by("-z_createdTimeStamp")

    templates = DME_Email_Templates.objects.filter(emailName="Status Update")
    emailVarList = {
        "FULLNAME": booking.de_to_Contact_F_LName,
        "ORDER_INVOICE_NO":  booking.b_client_order_num if not booking.inv_dme_invoice_no else booking.inv_dme_invoice_no,
        "BODYREPEAT": "",
    }
    html = ""
    for template in templates:
        emailBody = template.emailBody

        emailVarList["USERNAME"] = sender
        emailVarList["BOOKIGNO"] = bookingId
        emailVarList["STATUS"] = status
        emailVarList["STATUS_URL"] = status_url

        for key in emailVarList.keys():
            emailBody = emailBody.replace(
                "{" + str(key) + "}",
                str(emailVarList[key]) if emailVarList[key] else "",
            )

        html += emailBody

    mime_type = "html"

    subject = "Your order has shipped"

    if settings.ENV in ["local", "dev"]:
        to_emails = [
            # "bookings@deliver-me.com.au",
            "petew@deliver-me.com.au",
            # "goldj@deliver-me.com.au",
            "greatroyalone@outlook.com",
        ]
        subject = f"FROM TEST SERVER - {subject}"
    else:
        to_emails = ["bookings@deliver-me.com.au"]

        if booking.pu_Email:
            to_emails.append(booking.pu_Email)
        if booking.de_Email:
            cc_emails.append(booking.de_Email)
        if booking.pu_email_Group:
            cc_emails = cc_emails + booking.pu_email_Group.split(",")
        if booking.de_Email_Group_Emails:
            cc_emails = cc_emails + booking.de_Email_Group_Emails.split(",")
        if booking.booking_Created_For_Email:
            cc_emails.append(booking.booking_Created_For_Email)

    send_email(to_emails, cc_emails, subject, html, ['./static/status_attachment.png'], mime_type)

    EmailLogs.objects.create(
        booking_id=bookingId,
        emailName="Status Update",
        to_emails=COMMASPACE.join(to_emails),
        cc_emails=COMMASPACE.join(cc_emails),
        z_createdTimeStamp=str(datetime.now()),
        z_createdByAccount=sender,
    )
