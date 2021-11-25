import json
import datetime
import requests
import logging

from django.conf import settings

from api.models import *

logger = logging.getLogger(__name__)

TEMPO_CREDENTIALS = {
    "api_url": "https://globalconnect.tempo.org/api/RAPickup/Bookings",
    "username": "Deliver.Me",
    "password": "dk45b_AM",
}


def push_via_api(booking, event_timestamp):
    LOG_ID = "[UPDATE TEMPO via API]"

    # Run only on PROD
    if settings.ENV != "prod":
        return False

    # Run only for "Tempo" Client
    if booking.kf_client_id != "461162D2-90C7-BF4E-A905-092A1A5F73F3":
        return False

    # Run only when `tempo_push` flag is `on`
    dme_option = DME_Options.objects.get(option_name="tempo_push")
    if int(dme_option.option_value) != 1:
        return False

    json_booking = {}
    json_booking["dmeBookingID"] = booking.b_bookingID_Visual
    # json_booking["clientSalesInvoice"] = booking.b_client_sales_inv_num
    # json_booking["clientOrderNo"] = booking.b_client_order_num
    json_booking["freightProvider"] = booking.vx_freight_provider
    json_booking["consignmentNo"] = booking.v_FPBookingNumber
    json_booking["status"] = booking.b_status
    json_booking["statusTimestamp"] = event_timestamp

    if event_timestamp and not isinstance(event_timestamp, str):
        json_booking["statusTimestamp"] = event_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    json_booking["bookedDate"] = booking.b_dateBookedDate

    if booking.b_dateBookedDate and not isinstance(booking.b_dateBookedDate, str):
        json_booking["bookedDate"] = booking.b_dateBookedDate.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    # Client Ref Number - i.e: 'CS00493466' | Gap/Ra - i.e: 'TRA57811'
    line_datas = booking.line_datas()
    clientRefNumber = "" if not line_datas else line_datas[0].clientRefNumber
    gapRa = "" if not line_datas else line_datas[0].gap_ra
    json_booking["clientRefNum"] = clientRefNumber
    json_booking["gapRa"] = gapRa

    # Cost
    json_booking["cost"] = (
        "Not available"
        if not booking.api_booking_quote
        else booking.api_booking_quote.client_mu_1_minimum_values
    )

    # DE info
    json_booking["deToEntity"] = booking.deToCompanyName
    json_booking["deToStreet1"] = booking.de_To_Address_Street_1
    json_booking["deToState"] = booking.de_To_Address_State
    json_booking["deToPostalCode"] = booking.de_To_Address_PostalCode
    json_booking["deToSuburb"] = booking.de_To_Address_Suburb
    json_booking["deToContactName"] = booking.de_to_Contact_F_LName
    json_booking["deToPhoneMain"] = booking.de_to_Phone_Main
    json_booking["deToEmail"] = booking.de_Email

    # PU info
    json_booking["puEntity"] = booking.puCompany
    json_booking["puStreet1"] = booking.pu_Address_Street_1
    json_booking["puState"] = booking.pu_Address_State
    json_booking["puPostalCode"] = booking.pu_Address_PostalCode
    json_booking["puSuburb"] = booking.pu_Address_Suburb
    json_booking["puContactName"] = booking.pu_Contact_F_L_Name
    json_booking["puPhoneMain"] = booking.pu_Phone_Main
    json_booking["puEmail"] = booking.pu_Email

    json_payload = {"data": [json_booking]}
    logger.info(f"{LOG_ID} Payload: {json_payload}")
    headers = {"content-type": "application/json", "GCDB-Request-Type": "APIRequest"}

    res = requests.post(
        TEMPO_CREDENTIALS["api_url"],
        auth=(TEMPO_CREDENTIALS["username"], TEMPO_CREDENTIALS["password"]),
        json=json_payload,
        headers=headers,
    )
    logger.info(f"{LOG_ID} Response: {res.status_code}, {res.content}")
    return True
