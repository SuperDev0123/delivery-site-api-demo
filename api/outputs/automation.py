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

def send_sms(message, phone_number):
	if ENV == 'test':
		account_sid = "AC3476f2ed21f2d16213f1ba58614f7c51"
		auth_token  = "670ab2e82cd4a4701fedb36a82579e6d"
	else:
		account_sid = settings.TWILIO['APP_SID']
		auth_token = settings.TWILIO['TOKEN']

	client = Client(account_sid, auth_token)

	if ENV == 'test':
		phone_number = "+17634069539"
		msg = client.messages.create(
	    to="+17634069539", 
	    from_="+15005550006",
	    body=message)
	else:
		msg = client.messages.create(
	    to=phone_number,
	    from_=settings.TWILIO['NUMBER'],
	    body=message)

	print('twilio sent msg id', msg.sid)


def send_status_update_email(bookingId, message, sender):
    html = message
    booking = Bookings.objects.get(pk=int(bookingId))
    cc_emails = []

    subject = f"Status Update - DME#{booking.b_bookingID_Visual} / Freight Provider# {booking.v_FPBookingNumber}"
    mime_type = "html"

    if settings.ENV in ["local", "dev"]:
        to_emails = [
            "bookings@deliver-me.com.au",
            "petew@deliver-me.com.au",
            "goldj@deliver-me.com.au",
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

    send_email(to_emails, cc_emails, subject, html, None, mime_type)

    EmailLogs.objects.create(
        booking_id=bookingId,
        emailName="Status Update",
        to_emails=COMMASPACE.join(to_emails),
        cc_emails=COMMASPACE.join(cc_emails),
        z_createdTimeStamp=str(datetime.now()),
        z_createdByAccount=sender,
    )
