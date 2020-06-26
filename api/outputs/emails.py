import sys, time
import os, base64
from datetime import datetime
from email.utils import COMMASPACE

from django.conf import settings

from api.models import *
from api.utils import send_email


def send_booking_email_using_template(bookingId, emailName, sender):
    templates = DME_Email_Templates.objects.filter(emailName=emailName)
    booking = Bookings.objects.get(pk=int(bookingId))
    booking_lines = Booking_lines.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).order_by("-z_createdTimeStamp")
    booking_lines_data = Booking_lines_data.objects.filter(
        fk_booking_id=booking.pk_booking_id
    ).order_by("-z_createdTimeStamp")

    gaps = []
    refs = []
    for lines_data in booking_lines_data:
        if lines_data.gap_ra:
            gaps.append(lines_data.gap_ra)

        if lines_data.clientRefNumber:
            refs.append(lines_data.clientRefNumber)

    totalQty = 0
    totalWeight = 0
    for booking_line in booking_lines:
        totalQty += booking_line.e_qty
        totalWeight += booking_line.e_qty * booking_line.e_weightPerEach

    files = []
    DMEBOOKINGNUMBER = booking.b_bookingID_Visual
    BOOKEDDATE = booking.b_dateBookedDate
    DELIVERYDATE = booking.s_21_Actual_Delivery_TimeStamp
    TOADDRESSCONTACT = f" {booking.pu_Contact_F_L_Name}"
    FUTILEREASON = booking.vx_futile_Booking_Notes
    BOOKING_NUMBER = booking.b_bookingID_Visual
    FREIGHT_PROVIDER = booking.vx_freight_provider
    FREIGHT_PROVIDER_BOOKING_NUMBER = booking.v_FPBookingNumber
    REFERENCE_NUMBER = booking.b_clientReference_RA_Numbers
    TOT_PACKAGES = totalQty
    TOT_CUBIC_WEIGHT = totalWeight
    SERVICE_TYPE = ""

    etd = None
    uom = None

    try:
        etd, uom = booking.get_etd()

        if etd:
            SERVICE_TYPE = f"{etd} {uom}"
    except:
        pass

    SERVICE = booking.vx_serviceName
    LATEST_PICKUP_TIME = booking.s_05_Latest_Pick_Up_Date_TimeSet
    LATEST_DELIVERY_TIME = booking.s_06_Latest_Delivery_Date_TimeSet
    DELIVERY_ETA = booking.z_calculated_ETA
    INSTRUCTIONS = booking.b_handling_Instructions

    PICKUP_CONTACT = f"{booking.pu_Contact_F_L_Name} - {booking.pu_Phone_Main}"
    PICKUP_SUBURB = f"{booking.puCompany}, {booking.pu_Address_Suburb}"

    PICKUP_INSTRUCTIONS = ""
    if booking.pu_pickup_instructions_address:
        PICKUP_INSTRUCTIONS = f"{booking.pu_pickup_instructions_address}"
    if booking.pu_PickUp_Instructions_Contact:
        PICKUP_INSTRUCTIONS += f" {booking.pu_PickUp_Instructions_Contact}"

    PICKUP_OPERATING_HOURS = booking.pu_Operting_Hours
    DELIVERY_CONTACT = f"{booking.de_to_Contact_F_LName} - {booking.de_to_Phone_Main}"
    DELIVERY_SUBURB = f"{booking.deToCompanyName}, {booking.de_To_Address_Suburb}"

    DELIVERY_INSTRUCTIONS = ""
    if booking.de_to_PickUp_Instructions_Address:
        DELIVERY_INSTRUCTIONS = f"{booking.de_to_PickUp_Instructions_Address}"
    if booking.de_to_Pick_Up_Instructions_Contact:
        DELIVERY_INSTRUCTIONS += f" {booking.de_to_Pick_Up_Instructions_Contact}"

    DELIVERY_OPERATING_HOURS = booking.de_Operating_Hours
    ATTENTION_NOTES = booking.DME_Notes

    if emailName == "General Booking":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": ", ".join(refs),
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
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
            "BODYREPEAT": "",
        }

        if booking.z_label_url is not None and len(booking.z_label_url) is not 0:
            if settings.ENV == "local":
                files.append("./static/pdfs/" + booking.z_label_url)
            else:
                files.append("/opt/s3_public/pdfs/" + booking.z_label_url)
    elif emailName == "Return Booking":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": ", ".join(refs),
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
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
            "BODYREPEAT": "",
        }

        if booking.z_label_url is not None and len(booking.z_label_url) is not 0:
            if settings.ENV == "local":
                files.append("./static/pdfs/" + booking.z_label_url)
            else:
                files.append("/opt/s3_public/pdfs/" + booking.z_label_url)
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
            "REFERENCE_NUMBER": ", ".join(refs),
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
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
            "BODYREPEAT": "",
        }

        if booking.z_pod_url is not None and len(booking.z_pod_url) is not 0:
            if settings.ENV == "local":
                files.append("./static/imgs/" + booking.z_pod_url)
            else:
                files.append("/opt/s3_public/imgs/" + booking.z_pod_url)
    elif emailName == "Futile Pickup":
        emailVarList = {
            "TOADDRESSCONTACT": TOADDRESSCONTACT,
            "FUTILEREASON": FUTILEREASON,
            "BOOKING_NUMBER": BOOKING_NUMBER,
            "FREIGHT_PROVIDER": FREIGHT_PROVIDER,
            "FREIGHT_PROVIDER_BOOKING_NUMBER": FREIGHT_PROVIDER_BOOKING_NUMBER,
            "REFERENCE_NUMBER": ", ".join(refs),
            "TOT_PACKAGES": TOT_PACKAGES,
            "TOT_CUBIC_WEIGHT": TOT_CUBIC_WEIGHT,
            "SERVICE_TYPE": SERVICE_TYPE,
            "SERVICE": SERVICE,
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
            "BODYREPEAT": "",
        }

        if booking.z_label_url is not None and len(booking.z_label_url) is not 0:
            if settings.ENV == "local":
                files.append("./static/pdfs/" + booking.z_label_url)
            else:
                files.append("/opt/s3_public/pdfs/" + booking.z_label_url)

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
    if booking.booking_Created_For_Email:
        cc_emails.append(booking.booking_Created_For_Email)

    if emailName == "General Booking":
        subject = f"Tempo Freight Booking - DME#{booking.b_bookingID_Visual} / Freight Provider# {booking.v_FPBookingNumber}"
    else:
        subject = f"Tempo {emailName} - DME#{booking.b_bookingID_Visual} / Freight Provider# {booking.v_FPBookingNumber}"
    mime_type = "html"
    send_email(to_emails, cc_emails, subject, html, files, mime_type)

    EmailLogs.objects.create(
        booking_id=bookingId,
        emailName=emailName,
        to_emails=COMMASPACE.join(to_emails),
        cc_emails=COMMASPACE.join(cc_emails),
        z_createdTimeStamp=str(datetime.now()),
        z_createdByAccount=sender,
    )
