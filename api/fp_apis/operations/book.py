import time as t
import json
import base64
import logging
import requests
from datetime import datetime

from api.common import status_history, trace_error
from api.utils import get_eta_pu_by, get_eta_de_by
from api.file_operations.directory import create_dir
from api.operations.email_senders import send_booking_status_email
from api.models import Log, Api_booking_confirmation_lines

from api.fp_apis.pre_check import pre_check_book
from api.fp_apis.payload_builder import get_book_payload
from api.fp_apis.update_by_json import update_biopak_with_booked_booking
from api.fp_apis.operations.common import _set_error

from api.fp_apis.constants import (
    DME_LEVEL_API_URL,
    S3_URL,
)


logger = logging.getLogger("dme_api")


def book(fp_name, booking, booker):
    _fp_name = fp_name.lower()
    error_msg = pre_check_book(booking)

    if error_msg:
        return False, error_msg

    try:
        payload = get_book_payload(booking, _fp_name)
    except Exception as e:
        trace_error.print()
        logger.info(f"#401 - Error while build payload: {e}")
        error_msg = f"Error while build payload {str(e)}"
        return False, error_msg

    logger.info(f"### Payload ({fp_name} book): {payload}")
    url = DME_LEVEL_API_URL + "/booking/bookconsignment"
    response = requests.post(url, params={}, json=payload)
    res_content = (
        response.content.decode("utf8").replace("'t", " not").replace("'", '"')
    )
    json_data = json.loads(res_content)
    s0 = json.dumps(json_data, indent=2, sort_keys=True, default=str)  # Just for visual
    logger.info(f"### Response ({fp_name} book): {s0}")

    if (
        response.status_code == 500
        and _fp_name in ["startrack", "auspost"]
        and "An internal system error" in json_data[0]["message"]
    ):
        for i in range(4):
            t.sleep(180)
            logger.info(f"### Payload ({fp_name} book): {payload}")
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response = requests.post(url, params={}, json=payload)
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            logger.info(f"### Response ({fp_name} book): {s0}")

            if response.status_code == 200:
                break

    if response.status_code == 200:
        try:
            if booking.vx_freight_provider.lower() in ["startrack", "auspost"]:
                booking.v_FPBookingNumber = json_data["items"][0]["tracking_details"][
                    "consignment_id"
                ]
            elif booking.vx_freight_provider.lower() == "hunter":
                booking.v_FPBookingNumber = json_data["consignmentNumber"]
                booking.jobNumber = json_data["jobNumber"]
                booking.jobDate = json_data["jobDate"]
            elif booking.vx_freight_provider.lower() == "tnt":
                booking.v_FPBookingNumber = (
                    f"DME{str(booking.b_bookingID_Visual).zfill(9)}"
                )
            elif booking.vx_freight_provider.lower() == "sendle":
                booking.v_FPBookingNumber = json_data["v_FPBookingNumber"]

            booking.fk_fp_pickup_id = json_data["consignmentNumber"]
            booking.s_05_Latest_Pick_Up_Date_TimeSet = get_eta_pu_by(booking)
            booking.s_06_Latest_Delivery_Date_TimeSet = get_eta_de_by(
                booking, booking.api_booking_quote
            )
            booking.b_dateBookedDate = datetime.now()
            booking.b_status = "Booked"
            booking.b_error_Capture = None
            booking.save()

            Log(
                request_payload=payload,
                request_status="SUCCESS",
                request_type=f"{fp_name.upper()} BOOK",
                response=res_content,
                fk_booking_id=booking.id,
            ).save()

            # Create new statusHistory
            status_history.create(booking, "Booked", booker)

            # Save Label for Hunter
            create_dir(f"{S3_URL}/pdfs/{_fp_name}_au")
            if _fp_name == "hunter":
                json_label_data = json.loads(response.content)
                file_name = (
                    f"hunter_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"
                )
                full_path = f"{S3_URL}/pdfs/{_fp_name}_au/{file_name}"

                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(json_label_data["shippingLabel"]))
                    f.close()
                    booking.z_label_url = f"{_fp_name}_au/{file_name}"
                    booking.save()

                    # Send email when GET_LABEL
                    email_template_name = "General Booking"

                    if booking.b_booking_Category == "Salvage Expense":
                        email_template_name = "Return Booking"

                    send_booking_status_email(booking.pk, email_template_name, booker)
            # Save Label for Capital
            elif _fp_name == "capital":
                json_label_data = json.loads(response.content)
                file_name = f"capital_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"
                full_path = f"{S3_URL}/pdfs/{_fp_name}_au/{file_name}"

                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(json_label_data["Label"]))
                    f.close()
                    booking.z_label_url = f"{_fp_name}_au/{file_name}"
                    booking.save()

                    # Send email when GET_LABEL
                    email_template_name = "General Booking"

                    if booking.b_booking_Category == "Salvage Expense":
                        email_template_name = "Return Booking"

                    send_booking_status_email(booking.pk, email_template_name, booker)
            # Save Label for Startrack and AusPost
            elif _fp_name in ["startrack", "auspost"]:
                Api_booking_confirmation_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                ).delete()

                for item in json_data["items"]:
                    book_con = Api_booking_confirmation_lines(
                        fk_booking_id=booking.pk_booking_id,
                        api_item_id=item["item_id"],
                    ).save()
            # Increase Conote Number and Manifest Count for DHL, kf_client_id of DHLPFM is hardcoded now
            elif _fp_name == "dhl":
                if booking.kf_client_id == "461162D2-90C7-BF4E-A905-000000000002":
                    booking.v_FPBookingNumber = f"DME{booking.b_bookingID_Visual}"
                    booking.save()
                else:
                    booking.v_FPBookingNumber = str(json_data["orderNumber"])
                    booking.save()

            if booking.b_client_name.lower() == "biopak":
                update_biopak_with_booked_booking(booking.pk)

            message = f"Successfully booked({booking.v_FPBookingNumber})"
            return True, message
        except KeyError as e:
            trace_error.print()
            Log(
                request_payload=payload,
                request_status="ERROR",
                request_type=f"{fp_name.upper()} BOOK",
                response=res_content,
                fk_booking_id=booking.id,
            ).save()

            error_msg = s0
            _set_error(booking, error_msg)
            return False, error_msg
    elif response.status_code == 400:
        Log(
            request_payload=payload,
            request_status="ERROR",
            request_type=f"{fp_name.upper()} BOOK",
            response=res_content,
            fk_booking_id=booking.id,
        ).save()

        logger.error(f"[BOOK] - {str(res_content)}")

        if "errors" in json_data:
            error_msg = json_data["errors"]
        elif "errorMessage" in json_data:  # Sendle, TNT Error
            error_msg = json_data["errorMessage"]
        elif "errorMessage" in json_data[0]:
            error_msg = json_data[0]["errorMessage"]
        else:
            error_msg = res_content
        _set_error(booking, error_msg)
        return False, error_msg
    elif response.status_code == 500:
        Log(
            request_payload=payload,
            request_status="ERROR",
            request_type=f"{fp_name.upper()} BOOK",
            response=res_content,
            fk_booking_id=booking.id,
        ).save()

        error_msg = "DME bot: Tried booking 3-4 times seems to be an unknown issue. Please review and contact support if needed"
        _set_error(booking, error_msg)
        return False, error_msg
