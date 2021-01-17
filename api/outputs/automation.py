import sys, time
import os, base64
from datetime import datetime
from email.utils import COMMASPACE

from django.conf import settings

from api.models import DME_SMS_Templates, Bookings, Booking_lines, DME_Email_Templates
from twilio.rest import Client
from api.utils import send_email


def send_sms(phone_number, bookingId, status, sender, status_url):
    # html = message

    client = Client(settings.TWILIO["APP_SID"], settings.TWILIO["TOKEN"])
    template = DME_SMS_Templates.objects.filter(smsName="Status Update").first()
    smsMessage = template.smsMessage
    message = smsMessage.format(
        USERNAME=sender, BOOKIGNO=bookingId, STATUS=status, STATUS_URL=status_url
    )
    msg = client.messages.create(
        to=phone_number, from_=settings.TWILIO["NUMBER"], body=message
    )


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
        "ORDER_INVOICE_NO": booking.b_client_order_num
        if not booking.inv_dme_invoice_no
        else booking.inv_dme_invoice_no,
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

    send_email(
        to_emails,
        cc_emails,
        subject,
        html,
        ["./static/status_attachment.png"],
        mime_type,
    )

    EmailLogs.objects.create(
        booking_id=bookingId,
        emailName="Status Update",
        to_emails=COMMASPACE.join(to_emails),
        cc_emails=COMMASPACE.join(cc_emails),
        z_createdTimeStamp=str(datetime.now()),
        z_createdByAccount=sender,
    )
