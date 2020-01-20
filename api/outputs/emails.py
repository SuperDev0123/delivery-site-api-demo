import smtplib
import sys, time
import os, base64
import datetime
import email
import email.mime.application
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email.mime.text import MIMEText

from api.models import *
from api.utils import send_email

# start function to preprocess email booking from db table
def send_booking_email_using_template(bookingId, emailName):
    templates = DME_Email_Templates.objects.filter(emailName=emailName)
    booking = Bookings.objects.get(pk=int(bookingId))
    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

    totalQty = 0
    totalWeight = 0
    for booking_line in booking_lines:
        totalQty += booking_line.e_qty
        totalWeight += booking_line.e_qty * booking_line.e_weightPerEach

    label_files = []
    DMEBOOKINGNUMBER = booking.b_bookingID_Visual
    BOOKEDDATE = booking.b_dateBookedDate
    DELIVERYDATE = booking.s_21_Actual_Delivery_TimeStamp
    TOADDRESSCONTACT = booking.de_to_Contact_F_LName
    FUTILEREASON = booking.vx_futile_Booking_Notes
    BOOKING_NUMBER = booking.b_bookingID_Visual
    FREIGHT_PROVIDER = booking.vx_freight_provider
    FREIGHT_PROVIDER_BOOKING_NUMBER = booking.v_FPBookingNumber
    REFERENCE_NUMBER = booking.b_clientReference_RA_Numbers
    TOT_PACKAGES = totalQty
    TOT_CUBIC_WEIGHT = totalWeight
    SERVICE_TYPE = booking.vx_freight_provider_carrier
    SERVICE = booking.vx_serviceName
    MAX_TRANSIT_DURATION = booking.vx_Transit_Duration
    LATEST_PICKUP_TIME = booking.vx_fp_pu_eta_time
    LATEST_DELIVERY_TIME = booking.vx_fp_del_eta_time
    DELIVERY_ETA = booking.z_calculated_ETA
    INSTRUCTIONS = booking.b_handling_Instructions
    PICKUP_CONTACT = booking.pu_Contact_F_L_Name
    PICKUP_SUBURB = booking.pu_Address_Suburb
    PICKUP_INSTRUCTIONS = booking.de_to_PickUp_Instructions_Address
    PICKUP_OPERATING_HOURS = booking.pu_Operting_Hours
    DELIVERY_CONTACT = booking.de_to_Contact_F_LName
    DELIVERY_SUBURB = booking.de_To_Address_Suburb
    DELIVERY_INSTRUCTIONS = booking.de_to_PickUp_Instructions_Address
    DELIVERY_OPERATING_HOURS = booking.de_Operating_Hours
    ATTENTION_NOTES = booking.DME_Notes

    if emailName == "General Booking":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": REFERENCE_NUMBER,
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
            "MAX_TRANSIT_DURATION": MAX_TRANSIT_DURATION,
            "LATEST_PICKUP_TIME": LATEST_PICKUP_TIME,
            "LATEST_DELIVERY_TIME": LATEST_DELIVERY_TIME,
            "DELIVERY_ETA": DELIVERY_ETA,
            "INSTRUCTIONS": INSTRUCTIONS,
            "PICKUP_CONTACT": PICKUP_CONTACT,
            "PICKUP_SUBURB": PICKUP_SUBURB,
            "PICKUP_INSTRUCTIONS": PICKUP_INSTRUCTIONS,
            "PICKUP_OPERATING_HOURS": PICKUP_OPERATING_HOURS,
            "DELIVERY_CONTACT": DELIVERY_CONTACT,
            "DELIVERY_SUBURB": DELIVERY_SUBURB,
            "DELIVERY_INSTRUCTIONS": DELIVERY_INSTRUCTIONS,
            "DELIVERY_OPERATING_HOURS": DELIVERY_OPERATING_HOURS,
            "ATTENTION_NOTES": ATTENTION_NOTES,
        }

        if booking.z_label_url is not None and len(booking.z_label_url) is not 0:
            label_files.append("/opt/s3_public/pdfs/" + booking.z_label_url)

    elif emailName == "Return Booking":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": REFERENCE_NUMBER,
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
            "MAX_TRANSIT_DURATION": MAX_TRANSIT_DURATION,
            "LATEST_PICKUP_TIME": LATEST_PICKUP_TIME,
            "LATEST_DELIVERY_TIME": LATEST_DELIVERY_TIME,
            "DELIVERY_ETA": DELIVERY_ETA,
            "INSTRUCTIONS": INSTRUCTIONS,
            "PICKUP_CONTACT": PICKUP_CONTACT,
            "PICKUP_SUBURB": PICKUP_SUBURB,
            "PICKUP_INSTRUCTIONS": PICKUP_INSTRUCTIONS,
            "PICKUP_OPERATING_HOURS": PICKUP_OPERATING_HOURS,
            "DELIVERY_CONTACT": DELIVERY_CONTACT,
            "DELIVERY_SUBURB": DELIVERY_SUBURB,
            "DELIVERY_INSTRUCTIONS": DELIVERY_INSTRUCTIONS,
            "DELIVERY_OPERATING_HOURS": DELIVERY_OPERATING_HOURS,
            "ATTENTION_NOTES": ATTENTION_NOTES,
        }

    elif emailName == "POD":
        emailVarList = {
            "BOOKEDDATE": BOOKEDDATE,
            "DELIVERYDATE": DELIVERYDATE,
            "DMEBOOKINGNUMBER": DMEBOOKINGNUMBER,
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": REFERENCE_NUMBER,
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
            "MAX_TRANSIT_DURATION": MAX_TRANSIT_DURATION,
            "LATEST_PICKUP_TIME": LATEST_PICKUP_TIME,
            "LATEST_DELIVERY_TIME": LATEST_DELIVERY_TIME,
            "DELIVERY_ETA": DELIVERY_ETA,
            "INSTRUCTIONS": INSTRUCTIONS,
            "PICKUP_CONTACT": PICKUP_CONTACT,
            "PICKUP_SUBURB": PICKUP_SUBURB,
            "PICKUP_INSTRUCTIONS": PICKUP_INSTRUCTIONS,
            "PICKUP_OPERATING_HOURS": PICKUP_OPERATING_HOURS,
            "DELIVERY_CONTACT": DELIVERY_CONTACT,
            "DELIVERY_SUBURB": DELIVERY_SUBURB,
            "DELIVERY_INSTRUCTIONS": DELIVERY_INSTRUCTIONS,
            "DELIVERY_OPERATING_HOURS": DELIVERY_OPERATING_HOURS,
            "ATTENTION_NOTES": ATTENTION_NOTES,
        }

    elif emailName == "Futile Pickup":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": REFERENCE_NUMBER,
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
            "MAX_TRANSIT_DURATION": MAX_TRANSIT_DURATION,
            "LATEST_PICKUP_TIME": LATEST_PICKUP_TIME,
            "LATEST_DELIVERY_TIME": LATEST_DELIVERY_TIME,
            "DELIVERY_ETA": DELIVERY_ETA,
            "INSTRUCTIONS": INSTRUCTIONS,
            "PICKUP_CONTACT": PICKUP_CONTACT,
            "PICKUP_SUBURB": PICKUP_SUBURB,
            "PICKUP_INSTRUCTIONS": PICKUP_INSTRUCTIONS,
            "PICKUP_OPERATING_HOURS": PICKUP_OPERATING_HOURS,
            "DELIVERY_CONTACT": DELIVERY_CONTACT,
            "DELIVERY_SUBURB": DELIVERY_SUBURB,
            "DELIVERY_INSTRUCTIONS": DELIVERY_INSTRUCTIONS,
            "DELIVERY_OPERATING_HOURS": DELIVERY_OPERATING_HOURS,
            "ATTENTION_NOTES": ATTENTION_NOTES,
        }

    html = ""
    for template in templates:
        emailBody = template.emailBody
        emailBodyRepeatEven = (
            str(template.emailBodyRepeatEven) if template.emailBodyRepeatEven else ""
        )
        emailBodyRepeatOdd = (
            str(template.emailBodyRepeatOdd) if template.emailBodyRepeatOdd else ""
        )

        for idx, booking_line in enumerate(booking_lines):
            PRODUCT = str(booking_line.e_item) if booking_line.e_item else ""
            RA = (
                str(booking_line.e_spec_clientRMA_Number)
                if booking_line.e_spec_clientRMA_Number
                else ""
            )
            DESCRIPTION = str(booking_line.e_item) if booking_line.e_item else ""
            QTY = str(booking_line.e_qty) if booking_line.e_qty else ""
            REF = (
                str(booking_line.client_item_reference)
                if booking_line.client_item_reference
                else ""
            )
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

            if (idx % 2) == 0:
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

            else:
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

        emailVarList["BODYREPEAT"] = emailBodyRepeatOdd + emailBodyRepeatEven

        # print(emailVarList)

        for key in emailVarList.keys():
            emailBody = emailBody.replace(
                "{" + str(key) + "}",
                str(emailVarList[key]) if emailVarList[key] else "",
            )

        html += emailBody

    # TEST Use
    # fp1 = open("dme_booking_email_" + emailName + ".html", "w+")
    # fp1.write(html)

    to_emails = ["bookings@deliver-me.com.au"]
    if booking.pu_Email:
        to_emails.append(booking.pu_Email)
    if booking.pu_email_Group:
        to_emails.append(booking.pu_email_Group)
    if booking.de_Email_Group_Emails:
        to_emails.append(booking.de_Email_Group_Emails)
    if booking.booking_Created_For_Email:
        to_emails.append(booking.booking_Created_For_Email)

    subject = f"Tempo {emailName} - DME#{booking.v_FPBookingNumber} - FP#{booking.vx_freight_provider}"
    mime_type = "html"
    send_email(to_emails, subject, html, label_files, mime_type)


def send_bookings(email_addr, booking_ids):
    header = """
        <figure class="table">
            <table>
                <tbody>
                    <tr>
                        <td colspan="3">Hi {TOADDRESSCONTACT},</td></tr><tr><td colspan="3">&nbsp;</td>
                    </tr>
                    <tr>
                        <td colspan="3">Please book this in for tomorrow and let me know how many vehicles are you going to use. Please ask the driver to have the attached delivery dockets signed by the store as it will serve as the POD. Thank you.</td>
                    </tr>
                    <tr>
                        <td colspan="3"><strong>Will be collected from ACFS. Please ask the driver to go through the breezeway to avoid longer waiting time.&nbsp;</strong></td>
                    </tr>
                    <tr>
                        <td colspan="3">&nbsp;</td></tr><tr><td>Delivery window is between {DELIVERY_OPERATING_HOURS}.</td><td>&nbsp;</td>
                    </tr>
                    <tr>
                        <td colspan="3">&nbsp;</td></tr><tr><td>these are the bookings that are checked on all bookings page.</td><td>&nbsp;</td><td>&nbsp;</td>
                    </tr>
                </tbody>
            </table>
        </figure>
    """

    footer = """
        <figure class="table">
        <TABLE style = 'border-collapse: collapse; font-family: verdana; text-align: justify; text-justify: inter-word;line-height: 7px;'>
            <tr>
                <TD colspan = '3' width = '600px'>&nbsp;</TD>
            </tr>
            <tr>
                <TD colspan = '3' width = '600px'>&nbsp;</TD>
            </tr>
            <tr>
                <td colspan="3">Kind Regards,</td></tr><tr><td colspan="3">&nbsp;</td>
            </tr>
            <tr>
                <td colspan="3"><b>Nen - Bookings @ Deliver ME</b></td></tr><tr><td colspan="3">&nbsp;</td>
            </tr>
            <tr>
                <td colspan="3">DELIVER-ME PTY LTD</td></tr><tr><td colspan="3">&nbsp;</td>
            </tr>
            <tr>
                <td colspan="3"><b>T:</b> +61 2 8311 1500 <b>E:</b> bookings@deliver-me.com.au</td></tr><tr><td colspan="3">&nbsp;</td>
            </tr>
        </TABLE>
        </figure>
    """

    html = """\
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html>

    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>A responsive two column example</title>
        
    </head>

    <body>"""

    html += header

    html += """ 
        <figure class="table">   
        <table border="1" cellpadding="5" style = 'border-collapse: collapse; font-family: verdana;'>
            <thead>
                <TR style='color:#ffffff; '>
                <TD height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Document No.</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Location Code</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Order Number</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>External Document No.</TD>
                <TD height='25px' width = '100px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Sell-to Customer No.</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Sell-to Customer Name</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Ship-to Name</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Ship-to Address</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Ship-to City</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Ship-to Country</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Ship-to Postcode</TD>
                <TD height='25px' width = '200px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #fff1c6; color: #000000; text-align: center'>Pallet Count</TD>
              </TR>
            </thead>
        <tbody>
        </figure>
    """

    bookings = Bookings.objects.filter(pk__in=booking_ids)
    for booking in bookings:
        booking_lines = Booking_lines.objects.filter(
            fk_booking_id=booking.pk_booking_id
        )

        totalQty = 0
        totalWeight = 0
        for booking_line in booking_lines:
            totalQty = totalQty + booking_line.e_qty if booking_line.e_qty else 0
            totalWeight = (
                totalWeight + booking_line.e_Total_KG_weight
                if booking_line.e_Total_KG_weight
                else 0
            )
        html += """
            <tr>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
                <td height='25px' width = '900px' style='font-weight: bold; border:1px solid #b3b3b3; background-color: #ffffff; text-align: center'>%s</td>
            </tr>
            """ % (
            booking.b_bookingID_Visual,
            booking.de_To_Address_Suburb,
            booking.vx_fp_order_id,
            booking.fp_invoice_no,
            booking.de_to_Phone_Main,
            booking.de_to_Contact_F_LName,
            booking.de_to_Contact_F_LName,
            booking.de_To_Address_Street_1,
            booking.de_To_Address_City,
            booking.de_To_Address_Country,
            booking.de_To_Address_PostalCode,
            totalQty,
        )

    html += footer
    html += "</body></html>"

    # fp1 = open("dme_booking_process_email.html", "w+")
    # fp1.write(html)

    to_emails = [email_addr, "bookings@deliver-me.com.au"]
    subject = f"Tempo"
    mime_type = "html"
    send_email(to_emails, subject, html, None, mime_type)
