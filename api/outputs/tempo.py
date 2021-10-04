import json
import datetime
import requests
import logging

from django.conf import settings

from api.models import *

logger = logging.getLogger(__name__)

TEMPO_CREDENTIALS = {
    "host_url": "https://globalconnect.tempo.org/",
    "api_url": "https://globalconnect.tempo.org/api/EDIDelivery/Items",
    "username": "Deliver.Me",
    "password": "P93xVv2T",
}


def push_via_api(booking):
    if not settings.ENV == "prod":
        return False

    dme_option = DME_Options.objects.get(option_name="tempo_push")

    if (
        booking.kf_client_id == "461162D2-90C7-BF4E-A905-092A1A5F73F3"
        and int(dme_option.option_value) == 1
    ):
        json_booking = {}
        json_booking["bookedDate"] = booking.b_dateBookedDate

        if booking.b_dateBookedDate and not isinstance(booking.b_dateBookedDate, str):
            json_booking["bookedDate"] = booking.b_dateBookedDate.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        json_booking["fromState"] = booking.de_To_Address_State
        json_booking["toEntity"] = booking.deToCompanyName
        json_booking["toPostalCode"] = booking.de_To_Address_PostalCode
        json_booking["clientSalesInvoice"] = booking.b_client_sales_inv_num
        json_booking["clientOrderNo"] = booking.b_client_order_num
        json_booking["freightProvider"] = booking.vx_freight_provider
        json_booking["consignmentNo"] = booking.v_FPBookingNumber
        json_booking["status"] = booking.b_status
        json_booking["bookingID"] = booking.b_bookingID_Visual

        logger.info(f"@591 - {json_booking}")
        json_payload = {"data": [json_booking]}
        headers = {"content-type": "application/json"}

        res = requests.post(
            TEMPO_CREDENTIALS["api_url"],
            auth=(TEMPO_CREDENTIALS["username"], TEMPO_CREDENTIALS["password"]),
            json=json_payload,
            headers=headers,
        )
        logger.info(f"@592 - {res.status_code}, {res.content}")
