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


def send_status_update_email(bookingId, subject, message, sender):
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

        for idx, booking_line in enumerate(booking_lines):
            descriptions = []
            modelNumbers = []
            gaps = []
            refs = []

            booking_lines_data = Booking_lines_data.objects.filter(
                fk_booking_lines_id=booking_line.pk_booking_lines_id
            )

            for line_data in booking_lines_data:
                if line_data.itemDescription:
                    descriptions.append(line_data.itemDescription)

                if line_data.gap_ra:
                    gaps.append(line_data.gap_ra)

                if line_data.clientRefNumber:
                    refs.append(line_data.clientRefNumber)

                if line_data.modelNumber:
                    modelNumbers.append(line_data.modelNumber)

            REF = ", ".join(refs)
            RA = ", ".join(gaps)
            DESCRIPTION = ", ".join(descriptions)
            PRODUCT = ", ".join(modelNumbers)
            QTY = str(booking_line.e_qty) if booking_line.e_qty else ""
            TYPE = (
                str(booking_line.e_type_of_packaging)
                if booking_line.e_type_of_packaging
                else ""
            )
            LENGTH = (
                (str(booking_line.e_dimLength) if booking_line.e_dimLength else "")
                + " X "
                + (str(booking_line.e_dimWidth) if booking_line.e_dimWidth else "")
                + " X "
                + (str(booking_line.e_dimHeight) if booking_line.e_dimHeight else "")
                + " "
                + (str(booking_line.e_dimUOM) if booking_line.e_dimUOM else "")
            )
            WEIGHT = (
                (
                    str(booking_line.e_Total_KG_weight)
                    if booking_line.e_Total_KG_weight
                    else ""
                )
                + " "
                + (str(booking_line.e_weightUOM) if booking_line.e_weightUOM else "")
            )

            if idx % 2 == 0:
                emailBodyRepeatEven = (
                    str(template.emailBodyRepeatEven)
                    if template.emailBodyRepeatEven
                    else ""
                )
                emailVarListEven = {
                    "PRODUCT": PRODUCT,
                    "RA": RA,
                    "DESCRIPTION": DESCRIPTION,
                    "QTY": QTY,
                    "REF": REF,
                    "TYPE": TYPE,
                    "LENGTH": LENGTH,
                    "WEIGHT": WEIGHT,
                }

                for key in emailVarListEven.keys():
                    emailBodyRepeatEven = emailBodyRepeatEven.replace(
                        "{" + str(key) + "}",
                        str(emailVarListEven[key]) if emailVarListEven[key] else "",
                    )

                emailVarList["BODYREPEAT"] += emailBodyRepeatEven
            else:
                emailBodyRepeatOdd = (
                    str(template.emailBodyRepeatOdd)
                    if template.emailBodyRepeatOdd
                    else ""
                )
                emailVarListOdd = {
                    "PRODUCT": PRODUCT,
                    "RA": RA,
                    "DESCRIPTION": DESCRIPTION,
                    "QTY": QTY,
                    "REF": REF,
                    "TYPE": TYPE,
                    "LENGTH": LENGTH,
                    "WEIGHT": WEIGHT,
                }

                for key in emailVarListOdd.keys():
                    emailBodyRepeatOdd = emailBodyRepeatOdd.replace(
                        "{" + str(key) + "}",
                        str(emailVarListOdd[key]) if emailVarListOdd[key] else "",
                    )

                emailVarList["BODYREPEAT"] += emailBodyRepeatOdd

        for key in emailVarList.keys():
            emailBody = emailBody.replace(
                "{" + str(key) + "}",
                str(emailVarList[key]) if emailVarList[key] else "",
            )

        html += emailBody
        emailVarList["BODYREPEAT"] = ""

    
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

    send_email(to_emails, cc_emails, subject, html, None, mime_type)

    EmailLogs.objects.create(
        booking_id=bookingId,
        emailName="Status Update",
        to_emails=COMMASPACE.join(to_emails),
        cc_emails=COMMASPACE.join(cc_emails),
        z_createdTimeStamp=str(datetime.now()),
        z_createdByAccount=sender,
    )
