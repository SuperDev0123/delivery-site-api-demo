import sys, time
import os, base64
import datetime
from django.conf import settings

from api.models import *
from api.utils import send_email

# start function to preprocess email booking from db table
def send_booking_email_using_template(bookingId, emailName):
    templates = DME_Email_Templates.objects.filter(emailName=emailName)
    booking = Bookings.objects.get(pk=int(bookingId))
    booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
    booking_lines_data = Booking_lines_data.objects.filter(
        fk_booking_id=booking.pk_booking_id
    )

    totalQty = 0
    totalWeight = 0
    for booking_line in booking_lines:
        totalQty += booking_line.e_qty
        totalWeight += booking_line.e_qty * booking_line.e_weightPerEach

    files = []
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
            files.append("/opt/s3_public/pdfs/" + booking.z_label_url)

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

        if booking.z_pod_url is not None and len(booking.z_pod_url) is not 0:
            files.append("/opt/s3_public/pdfs/" + booking.z_pod_url)

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

        gaps = []

        for lines_data in booking_lines_data:
            if lines_data.gap_ra:
                gaps.append(lines_data.gap_ra)

        for idx, booking_line in enumerate(booking_lines):
            PRODUCT = str(booking_line.e_item) if booking_line.e_item else ""
            RA = ", ".join(gaps)
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

        for key in emailVarList.keys():
            emailBody = emailBody.replace(
                "{" + str(key) + "}",
                str(emailVarList[key]) if emailVarList[key] else "",
            )

        html += emailBody

    # TEST Usage
    # fp1 = open("dme_booking_email_" + emailName + ".html", "w+")
    # fp1.write(html)

    if settings.ENV in ["local", "dev"]:
        to_emails = ["petew@deliver-me.com.au", "goldj@deliver-me.com.au"]
    else:
        to_emails = ["bookings@deliver-me.com.au"]

    cc_emails = []

    if booking.pu_Email:
        to_emails.append(booking.pu_Email)
    if booking.de_Email:
        cc_emails.append(booking.de_Email)
    if booking.pu_email_Group:
        cc_emails = cc_emails + booking.pu_email_Group.split(",")
    if booking.de_Email_Group_Emails:
        cc_emails = cc_emails + booking.de_Email_Group_Emails.split(",")
    if booking.de_Email_Group_Emails:
        cc_emails = cc_emails + booking.de_Email_Group_Emails.split(",")

    if emailName == "General Booking":
        subject = f"Tempo Freight Booking - DME#{booking.b_bookingID_Visual}/{booking.vx_freight_provider} #{booking.v_FPBookingNumber}"
    else:
        subject = f"Tempo {emailName} - DME#{booking.b_bookingID_Visual}/{booking.vx_freight_provider} #{booking.v_FPBookingNumber}"
    mime_type = "html"
    send_email(to_emails, cc_emails, subject, html, files, mime_type)
