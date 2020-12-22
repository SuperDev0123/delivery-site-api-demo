import time as t
import json
import requests
import requests_async
import datetime
import base64
import os
import logging
import asyncio
from ast import literal_eval

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.http import JsonResponse
from django.conf import settings

from api.models import *
from api.serializers import ApiBookingQuotesSerializer
from api.common import status_history, download_external, trace_error
from api.common.build_object import Struct
from api.file_operations.directory import create_dir_if_not_exist
from api.file_operations.downloads import download_from_url
from api.utils import get_eta_pu_by, get_eta_de_by
from api.operations.email_senders import send_booking_status_email

from .payload_builder import *
from .self_pricing import get_pricing as get_self_pricing
from .utils import (
    get_dme_status_from_fp_status,
    auto_select_pricing,
)
from .response_parser import *
from .pre_check import *
from .update_by_json import update_biopak_with_booked_booking
from api.operations.labels.index import build_label
from .operations.tracking import update_booking_with_tracking_result
from .constants import (
    FP_CREDENTIALS,
    BUILT_IN_PRICINGS,
    PRICING_TIME,
    AVAILABLE_FPS_4_FC,
)

if settings.ENV == "local":
    IS_PRODUCTION = False  # Local
else:
    IS_PRODUCTION = True  # Dev

if settings.ENV == "local":
    DME_LEVEL_API_URL = "http://localhost:3000"
elif settings.ENV == "dev":
    DME_LEVEL_API_URL = "http://52.62.109.115:3000"
elif settings.ENV == "prod":
    DME_LEVEL_API_URL = "http://52.62.102.72:3000"

logger = logging.getLogger("dme_api")


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def tracking(request, fp_name):
    body = literal_eval(request.body.decode("utf8"))
    booking_id = body["booking_id"]

    try:
        booking = Bookings.objects.get(id=booking_id)
        payload = get_tracking_payload(booking, fp_name)

        logger.info(f"### Payload ({fp_name} tracking): {payload}")
        url = DME_LEVEL_API_URL + "/tracking/trackconsignment"
        response = requests.post(url, params={}, json=payload)

        if fp_name.lower() in ["tnt"]:
            res_content = response.content.decode("utf8")
        else:
            res_content = response.content.decode("utf8").replace("'", '"')

        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### Response ({fp_name} tracking): {s0}")

        try:
            Log(
                request_payload=payload,
                request_status="SUCCESS",
                request_type=f"{fp_name.upper()} TRACKING",
                response=res_content,
                fk_booking_id=booking.id,
            ).save()

            consignmentTrackDetails = json_data["consignmentTrackDetails"][0]
            consignmentStatuses = consignmentTrackDetails["consignmentStatuses"]
            update_booking_with_tracking_result(
                request, booking, fp_name, consignmentStatuses
            )
            booking.b_error_Capture = None
            booking.save()

            return JsonResponse(
                {
                    "message": f"DME status: {booking.b_status},FP status: {booking.b_status_API}",
                    "b_status": booking.b_status,
                    "b_status_API": booking.b_status_API,
                },
                status=status.HTTP_200_OK,
            )
        except KeyError:
            if "errorMessage" in json_data:
                error_msg = json_data["errorMessage"]
                _set_error(booking, error_msg)
                logger.info(f"#510 ERROR: {error_msg}")
            else:
                error_msg = "Failed Tracking"

            trace_error.print()
            return JsonResponse(
                {"error": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )
    except Bookings.DoesNotExist:
        trace_error.print()
        logger.info(f"#511 ERROR: {e}")
        return JsonResponse(
            {"message": "Booking not found"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        trace_error.print()
        logger.info(f"#512 ERROR: {e}")
        return JsonResponse(
            {"message": "Tracking failed"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def book(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        _fp_name = fp_name.lower()

        try:
            booking = Bookings.objects.get(id=booking_id)
            error_msg = pre_check_book(booking)

            if error_msg:
                return JsonResponse(
                    {"message": f"#700 Error: {error_msg}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                payload = get_book_payload(booking, _fp_name)
            except Exception as e:
                trace_error.print()
                logger.info(f"#401 - Error while build payload: {e}")
                return JsonResponse(
                    {"message": f"Error while build payload {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(f"### Payload ({fp_name} book): {payload}")
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response = requests.post(url, params={}, json=payload)
            res_content = (
                response.content.decode("utf8").replace("'t", " not").replace("'", '"')
            )
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            logger.info(f"### Response ({fp_name} book): {s0}")

            if (
                response.status_code == 500
                and _fp_name == "startrack"
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
                    request_payload = {
                        "apiUrl": "",
                        "accountCode": "",
                        "authKey": "",
                        "trackingId": "",
                    }
                    request_payload["apiUrl"] = url
                    request_payload["accountCode"] = payload["spAccountDetails"][
                        "accountCode"
                    ]
                    request_payload["authKey"] = payload["spAccountDetails"][
                        "accountKey"
                    ]
                    request_payload["trackingId"] = json_data["consignmentNumber"]

                    if booking.vx_freight_provider.lower() == "startrack":
                        booking.v_FPBookingNumber = json_data["items"][0][
                            "tracking_details"
                        ]["consignment_id"]
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
                        request_payload=request_payload,
                        request_status="SUCCESS",
                        request_type=f"{fp_name.upper()} BOOK",
                        response=res_content,
                        fk_booking_id=booking.id,
                    ).save()

                    # Create new statusHistory
                    status_history.create(booking, "Booked", request.user.username)

                    # Save Label for Hunter
                    create_dir_if_not_exist(f"./static/pdfs/{_fp_name}_au")
                    if booking.vx_freight_provider.lower() == "hunter":
                        json_label_data = json.loads(response.content)
                        file_name = f"hunter_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"

                        if IS_PRODUCTION:
                            file_url = f"/opt/s3_public/pdfs/{_fp_name}_au/{file_name}"
                        else:
                            file_url = f"./static/pdfs/{_fp_name}_au/{file_name}"

                        with open(file_url, "wb") as f:
                            f.write(base64.b64decode(json_label_data["shippingLabel"]))
                            f.close()
                            booking.z_label_url = f"hunter_au/{file_name}"
                            booking.save()

                            # Send email when GET_LABEL
                            email_template_name = "General Booking"

                            if booking.b_booking_Category == "Salvage Expense":
                                email_template_name = "Return Booking"

                            send_booking_status_email(
                                booking.pk, email_template_name, request.user.username
                            )
                    # Save Label for Capital
                    elif booking.vx_freight_provider.lower() == "capital":
                        json_label_data = json.loads(response.content)
                        file_name = f"capital_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"

                        if IS_PRODUCTION:
                            file_url = f"/opt/s3_public/pdfs/{_fp_name}_au/{file_name}"
                        else:
                            file_url = f"./static/pdfs/{_fp_name}_au/{file_name}"

                        with open(file_url, "wb") as f:
                            f.write(base64.b64decode(json_label_data["Label"]))
                            f.close()
                            booking.z_label_url = f"capital_au/{file_name}"
                            booking.save()

                            # Send email when GET_LABEL
                            email_template_name = "General Booking"

                            if booking.b_booking_Category == "Salvage Expense":
                                email_template_name = "Return Booking"

                            send_booking_status_email(
                                booking.pk, email_template_name, request.user.username
                            )
                    # Save Label for Startrack
                    elif booking.vx_freight_provider.lower() == "startrack":
                        Api_booking_confirmation_lines.objects.filter(
                            fk_booking_id=booking.pk_booking_id
                        ).delete()

                        for item in json_data["items"]:
                            book_con = Api_booking_confirmation_lines(
                                fk_booking_id=booking.pk_booking_id,
                                api_item_id=item["item_id"],
                            ).save()
                    # Increase Conote Number and Manifest Count for DHL, kf_client_id of DHLPFM is hardcoded now
                    elif booking.vx_freight_provider.lower() == "dhl":
                        if (
                            booking.kf_client_id
                            == "461162D2-90C7-BF4E-A905-000000000002"
                        ):
                            booking.v_FPBookingNumber = (
                                f"DME{booking.b_bookingID_Visual}"
                            )
                            booking.save()
                        else:
                            booking.v_FPBookingNumber = str(json_data["orderNumber"])
                            booking.save()

                    if booking.b_client_name.lower() == "biopak":
                        update_biopak_with_booked_booking(booking_id)

                    return JsonResponse(
                        {"message": f"Successfully booked({booking.v_FPBookingNumber})"}
                    )
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
                    return JsonResponse(
                        {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                    )
            elif response.status_code == 400:
                Log(
                    request_payload=payload,
                    request_status="ERROR",
                    request_type=f"{fp_name.upper()} BOOK",
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                if "errors" in json_data:
                    error_msg = json_data["errors"]
                elif "errorMessage" in json_data:  # Sendle, TNT Error
                    error_msg = json_data["errorMessage"]
                elif "errorMessage" in json_data[0]:
                    error_msg = json_data[0]["errorMessage"]
                else:
                    error_msg = s0
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
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
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            trace_error.print()
            error_msg = str(e)
            _set_error(booking, error_msg)
            return JsonResponse(
                {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )
    except SyntaxError as e:
        trace_error.print()
        return JsonResponse(
            {"message": f"SyntaxError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def rebook(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]

        try:
            booking = Bookings.objects.get(id=booking_id)

            error_msg = pre_check_rebook(booking)

            if error_msg:
                return JsonResponse(
                    {"message": f"#700 Error: {error_msg}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                payload = get_book_payload(booking, fp_name)
            except Exception as e:
                trace_error.print()
                logger.info(f"#401 - Error while build payload: {e}")
                return JsonResponse(
                    {"message": f"Error while build payload {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(f"### Payload ({fp_name} rebook): {payload}")
            url = DME_LEVEL_API_URL + "/booking/rebookconsignment"
            response = requests.post(url, params={}, json=payload)
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            logger.info(f"### Response ({fp_name} rebook): {s0}")

            if response.status_code == 200:
                try:
                    request_payload = {
                        "apiUrl": "",
                        "accountCode": "",
                        "authKey": "",
                        "trackingId": "",
                    }
                    request_payload["apiUrl"] = url
                    request_payload["accountCode"] = payload["spAccountDetails"][
                        "accountCode"
                    ]
                    request_payload["authKey"] = payload["spAccountDetails"][
                        "accountKey"
                    ]
                    request_payload["trackingId"] = json_data["consignmentNumber"]

                    if booking.vx_freight_provider.lower() == "tnt":
                        booking.v_FPBookingNumber = (
                            f"DME{str(booking.b_bookingID_Visual).zfill(9)}"
                        )

                    old_fk_fp_pickup_id = booking.fk_fp_pickup_id
                    booking.fk_fp_pickup_id = json_data["consignmentNumber"]
                    booking.b_dateBookedDate = datetime.now()
                    status_history.create(
                        booking,
                        "PU Rebooked(Last pickup Id was "
                        + str(old_fk_fp_pickup_id)
                        + ")",
                        request.user.username,
                    )
                    booking.b_status = "PU Rebooked"
                    booking.s_05_Latest_Pick_Up_Date_TimeSet = get_eta_pu_by(booking)
                    booking.s_06_Latest_Delivery_Date_TimeSet = get_eta_de_by(
                        booking, booking.api_booking_quote
                    )
                    booking.b_error_Capture = None
                    booking.save()

                    Log(
                        request_payload=request_payload,
                        request_status="SUCCESS",
                        request_type=f"{fp_name.upper()} REBOOK",
                        response=res_content,
                        fk_booking_id=booking.id,
                    ).save()

                    return JsonResponse(
                        {"message": f"Successfully booked({booking.v_FPBookingNumber})"}
                    )
                except KeyError as e:
                    trace_error.print()
                    Log(
                        request_payload=payload,
                        request_status="ERROR",
                        request_type=f"{fp_name.upper()} REBOOK",
                        response=res_content,
                        fk_booking_id=booking.id,
                    ).save()

                    error_msg = s0
                    _set_error(booking, error_msg)
                    return JsonResponse(
                        {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                    )
            elif response.status_code == 400:
                Log(
                    request_payload=payload,
                    request_status="ERROR",
                    request_type=f"{fp_name.upper()} REBOOK",
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                if "errors" in json_data:
                    error_msg = json_data["errors"]
                elif "errorMessage" in json_data:  # TNT Error
                    error_msg = json_data["errorMessage"]
                elif "errorMessage" in json_data[0]:  # Hunter Error
                    error_msg = json_data[0]["errorMessage"]
                else:
                    error_msg = s0
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
            elif response.status_code == 500:
                Log(
                    request_payload=payload,
                    request_status="ERROR",
                    request_type=f"{fp_name.upper()} REBOOK",
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                error_msg = "DME bot: Tried rebooking 3-4 times seems to be an unknown issue. Please review and contact support if needed"
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            trace_error.print()
            error_msg = str(e)
            _set_error(booking, error_msg)
            return JsonResponse(
                {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )
    except SyntaxError as e:
        trace_error.print()
        return JsonResponse(
            {"message": f"SyntaxError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def edit_book(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]

        try:
            booking = Bookings.objects.get(id=booking_id)

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                error_msg = "State for pickup postal address is required."
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg})
            elif booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                error_msg = "Suburb name for pickup postal address is required."
                _set_error(booking, error_msg)
                return booking_id({"message": error_msg})
            elif booking.z_manifest_url is not None or booking.z_manifest_url != "":
                error_msg = "This booking is manifested."
                _set_error(booking, error_msg)
                return booking_id({"message": error_msg})

            payload = get_book_payload(booking, fp_name)

            logger.info(f"### Payload ({fp_name} edit book): {payload}")
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response = requests.post(url, params={}, json=payload)
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            logger.info(f"### Response ({fp_name} edit book): {s0}")

            try:
                request_payload = {
                    "apiUrl": "",
                    "accountCode": "",
                    "authKey": "",
                    "trackingId": "",
                }
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = payload["spAccountDetails"][
                    "accountCode"
                ]
                request_payload["authKey"] = payload["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = json_data["consignmentNumber"]
                request_type = f"{fp_name.upper()} EDIT BOOK"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = json_data["items"][0]["tracking_details"][
                    "consignment_id"
                ]
                booking.fk_fp_pickup_id = json_data["consignmentNumber"]
                booking.b_dateBookedDate = datetime.now()
                booking.b_status = "Booked"
                booking.b_error_Capture = None
                booking.save()

                Log(
                    request_payload=request_payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                Api_booking_confirmation_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                ).delete()

                for item in json_data["items"]:
                    book_con = Api_booking_confirmation_lines(
                        fk_booking_id=booking.pk_booking_id, api_item_id=item["item_id"]
                    ).save()

                return JsonResponse(
                    {"message": f"Successfully edit book({booking.v_FPBookingNumber})"}
                )
            except KeyError as e:
                trace_error.print()
                Log(
                    request_payload=payload,
                    request_status="ERROR",
                    request_type=f"{fp_name.upper()} EDIT BOOK",
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                error_msg = s0
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
        except IndexError as e:
            trace_error.print()
            return JsonResponse(
                {"message": f"IndexError {e}"}, status=status.HTTP_400_BAD_REQUEST
            )
    except SyntaxError as e:
        trace_error.print()
        return JsonResponse(
            {"message": f"SyntaxError {e}"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def cancel_book(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        booking = Bookings.objects.get(id=booking_id)

        if booking.b_status != "Closed":
            if booking.b_dateBookedDate is not None:
                payload = get_cancel_book_payload(booking, fp_name)

                logger.info(f"### Payload ({fp_name} cancel book): {payload}")
                url = DME_LEVEL_API_URL + "/booking/cancelconsignment"
                response = requests.delete(url, params={}, json=payload)
                res_content = response.content.decode("utf8").replace("'", '"')
                json_data = json.loads(res_content)
                s0 = json.dumps(
                    json_data, indent=2, sort_keys=True, default=str
                )  # Just for visual
                logger.info(f"### Response ({fp_name} cancel book): {s0}")

                try:
                    if response.status_code == 200:
                        status_history.create(booking, "Closed", request.user.username)
                        booking.b_status = "Closed"
                        booking.b_dateBookedDate = None
                        booking.b_booking_Notes = (
                            "This booking has been closed vis Startrack API"
                        )
                        booking.b_error_Capture = None
                        booking.save()

                        Log(
                            request_payload=payload,
                            request_status="SUCCESS",
                            request_type=f"{fp_name.upper()} CANCEL BOOK",
                            response=res_content,
                            fk_booking_id=booking.id,
                        ).save()

                        return JsonResponse(
                            {"message": "Successfully cancelled book"},
                            status=status.HTTP_200_OK,
                        )
                    else:
                        if "errorMessage" in json_data:
                            error_msg = json_data["errorMessage"]
                            _set_error(booking, error_msg)
                            return JsonResponse(
                                {"message": error_msg},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        error_msg = json_data
                        _set_error(booking, error_msg)
                        return JsonResponse(
                            {"message": "Failed to cancel book"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                except KeyError as e:
                    trace_error.print()
                    Log(
                        request_payload=payload,
                        request_status="ERROR",
                        request_type=f"{fp_name.upper()} CANCEL BOOK",
                        response=res_content,
                        fk_booking_id=booking.id,
                    ).save()

                    error_msg = s0
                    _set_error(booking, error_msg)
                    return JsonResponse(
                        {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                error_msg = "Booking is not booked yet"
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return JsonResponse(
                {"message": "Booking is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except IndexError as e:
        trace_error.print()
        return JsonResponse(
            {"message": f"IndexError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )
    except SyntaxError as e:
        trace_error.print()
        return JsonResponse(
            {"message": f"SyntaxError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_label(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        booking = Bookings.objects.get(id=booking_id)
        _fp_name = fp_name.lower()

        error_msg = pre_check_label(booking)

        if error_msg:
            return JsonResponse(
                {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )

        payload = {}
        if _fp_name in ["startrack", "auspost"]:
            try:
                payload = get_create_label_payload(booking, _fp_name)

                logger.info(
                    f"### Payload ({fp_name} create_label): {json.dumps(payload, indent=2, sort_keys=True, default=str)}"
                )
                url = DME_LEVEL_API_URL + "/labelling/createlabel"
                response = requests.post(url, params={}, json=payload)
                res_content = response.content.decode("utf8").replace("'", '"')
                json_data = json.loads(res_content)
                s0 = json.dumps(
                    json_data, indent=2, sort_keys=True, default=str
                )  # Just for visual
                logger.info(f"### Response ({fp_name} create_label): {s0}")

                payload["consignmentNumber"] = json_data[0]["request_id"]
            except Exception as e:
                trace_error.print()
                request_type = f"{fp_name.upper()} CREATE LABEL"
                request_status = "ERROR"
                oneLog = Log(
                    request_payload=payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()

                error_msg = s0
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
        elif _fp_name in ["tnt", "sendle"]:
            payload = get_getlabel_payload(booking, fp_name)

        try:
            logger.info(f"### Payload ({fp_name} get_label): {payload}")
            url = DME_LEVEL_API_URL + "/labelling/getlabel"
            json_data = None

            while (
                json_data is None
                or (
                    json_data is not None
                    and _fp_name == "startrack"
                    and json_data["labels"][0]["status"] == "PENDING"
                )
                or (
                    json_data is not None
                    and _fp_name == "tnt"
                    and json_data["anyType"]["Status"] != "SUCCESS"
                )
            ):
                t.sleep(5)  # Delay to wait label is created
                response = requests.post(url, params={}, json=payload)
                res_content = response.content.decode("utf8").replace("'", '"')

                if _fp_name in ["sendle"]:
                    res_content = response.content.decode("utf8")

                json_data = json.loads(res_content)
                s0 = json.dumps(
                    json_data, indent=2, sort_keys=True, default=str
                )  # Just for visual
                logger.info(f"### Response ({fp_name} get_label): {s0}")

            if _fp_name in ["startrack"]:
                z_label_url = download_external.pdf(
                    json_data["labels"][0]["url"], booking
                )
            elif _fp_name in ["tnt", "sendle"]:
                try:
                    if _fp_name == "tnt":
                        label_data = base64.b64decode(json_data["anyType"]["LabelPDF"])
                        file_name = f"{fp_name}_label_{booking.pu_Address_State}_{booking.b_client_sales_inv_num}_{str(datetime.now())}.pdf"
                    elif _fp_name == "sendle":
                        file_name = f"{fp_name}_label_{booking.pu_Address_State}_{booking.v_FPBookingNumber}_{str(datetime.now())}.pdf"

                    z_label_url = f"{_fp_name}_au/{file_name}"

                    if settings.ENV == "prod":
                        label_url = f"/opt/s3_public/pdfs/{z_label_url}"
                    else:
                        label_url = f"./static/pdfs/{z_label_url}"

                    if _fp_name == "tnt":
                        with open(label_url, "wb") as f:
                            f.write(label_data)
                            f.close()
                    else:
                        pdf_url = json_data["pdfURL"]
                        download_from_url(pdf_url, label_url)
                except KeyError as e:
                    if "errorMessage" in json_data:
                        error_msg = json_data["errorMessage"]
                        _set_error(booking, error_msg)
                        return JsonResponse(
                            {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                        )

                    trace_error.print()
                    error_msg = f"KeyError: {e}"
                    _set_error(booking, error_msg)
            elif _fp_name in ["dhl"]:
                file_name = f"{fp_name}_label_{booking.pu_Address_State}_{booking.v_FPBookingNumber}_{str(datetime.now())}.pdf"
                z_label_url = f"{_fp_name}_au/{file_name}"

                if settings.ENV == "prod":
                    label_url = f"/opt/s3_public/pdfs/{z_label_url}"
                else:
                    label_url = f"./static/pdfs/{z_label_url}"

                build_label(booking, label_url)

            booking.z_label_url = z_label_url
            booking.b_error_Capture = None
            booking.save()

            # Do not send email when booking is `Rebooked`
            if not _fp_name in ["startrack"] and not "Rebooked" in booking.b_status:
                # Send email when GET_LABEL
                email_template_name = "General Booking"

                if booking.b_booking_Category == "Salvage Expense":
                    email_template_name = "Return Booking"

                send_booking_status_email(
                    booking.pk, email_template_name, request.user.username
                )

            if not _fp_name in ["sendle"]:
                Log(
                    request_payload=payload,
                    request_status="SUCCESS",
                    request_type=f"{fp_name.upper()} GET LABEL",
                    response=res_content,
                    fk_booking_id=booking.id,
                ).save()
            return JsonResponse(
                {"message": f"Successfully created label({booking.z_label_url})"},
                status=status.HTTP_200_OK,
            )
        except KeyError as e:
            trace_error.print()
            Log(
                request_payload=payload,
                request_status="ERROR",
                request_type=f"{fp_name.upper()} GET LABEL",
                response=res_content,
                fk_booking_id=booking.id,
            ).save()

            error_msg = s0

            if _fp_name in ["tnt"]:
                error_msg = json_data["errorMessage"]

            _set_error(booking, error_msg)
            return JsonResponse(
                {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )
    except IndexError as e:
        trace_error.print()
        return JsonResponse(
            {"message": "IndexError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def create_order(request, fp_name):
    results = []
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]

    try:
        bookings = Bookings.objects.filter(
            pk__in=booking_ids, b_status="Booked", vx_freight_provider__iexact=fp_name
        )

        payload = get_create_order_payload(bookings, fp_name)

        logger.info(f"Payload(Create Order for ST): {payload}")
        url = DME_LEVEL_API_URL + "/order/create"
        response = requests.post(url, params={}, json=payload)

        had_504_res = False
        while response.status_code == 504:
            had_504_res = True
            response = requests.post(url, params={}, json=payload)

        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(
            json_data, indent=2, sort_keys=True, default=str
        )  # Just for visual
        logger.info(f"Response(Create Order for ST): {s0}")

        try:
            Log(
                request_payload=payload,
                request_status="SUCCESS",
                request_type=f"{fp_name} CREATE ORDER",
                response=res_content,
                fk_booking_id=bookings[0].pk_booking_id,
            ).save()

            for booking in bookings:
                booking.vx_fp_order_id = (
                    json_data["order_id"]
                    if not had_504_res
                    else json_data[0]["context"]["order_id"]
                )
                booking.save()

            return JsonResponse(
                {"message": f"Successfully create order({booking.vx_fp_order_id})"}
            )
        except KeyError as e:
            trace_error.print()
            booking.b_error_Capture = json_data["errorMsg"]
            booking.save()
            Log(
                request_payload=payload,
                request_status="ERROR",
                request_type=f"{fp_name.upper()} CREATE ORDER",
                response=res_content,
                fk_booking_id=booking.id,
            ).save()

            error_msg = s0
            _set_error(booking, error_msg)
            return JsonResponse({"message": error_msg})
    except IndexError as e:
        trace_error.print()
        return JsonResponse({"message": f"IndexError: e"})


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_order_summary(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_ids = body["bookingIds"]
        _fp_name = fp_name.lower()

        try:
            booking = Bookings.objects.get(id=booking_ids[0])
            payload = get_get_order_summary_payload(booking, fp_name)
            headers = {"Accept": "application/pdf", "Content-Type": "application/json"}

            logger.info(f"### Payload ({fp_name} Get Order Summary): {payload}")
            url = DME_LEVEL_API_URL + "/order/summary"
            response = requests.post(url, json=payload, headers=headers)
            res_content = response.content
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # logger.info(f"### Response ({fp_name} Get Order Summary): {bytes(json_data["pdfData"]["data"])}")

            try:
                file_name = f"biopak_manifest_{str(booking.vx_fp_order_id)}_{str(datetime.now())}.pdf"

                if IS_PRODUCTION:
                    file_url = f"/opt/s3_public/pdfs/{_fp_name}_au/{file_name}"
                else:
                    file_url = f"./static/pdfs/{_fp_name}_au/{file_name}"

                create_dir_if_not_exist(f"./static/pdfs/{_fp_name}_au")
                with open(file_url, "wb") as f:
                    f.write(bytes(json_data["pdfData"]["data"]))
                    f.close()

                bookings = Bookings.objects.filter(pk__in=booking_ids)

                manifest_timestamp = datetime.now()
                for booking in bookings:
                    booking.z_manifest_url = f"{_fp_name}_au/{file_name}"
                    booking.manifest_timestamp = manifest_timestamp
                    booking.save()

                Log(
                    request_payload=payload,
                    request_status="SUCCESS",
                    request_type=f"{fp_name} GET ORDER SUMMARY",
                    response=res_content,
                    fk_booking_id=bookings[0].pk_booking_id,
                ).save()

                return JsonResponse({"message": "Manifest is created successfully."})
            except KeyError as e:
                trace_error.print()
                Log(
                    request_payload=payload,
                    request_status="FAILED",
                    request_type=f"{fp_name} GET ORDER SUMMARY",
                    response=res_content,
                    fk_booking_id=bookings[0].pk_booking_id,
                ).save()

                error_msg = s0
                _set_error(booking, error_msg)
                return JsonResponse({"message": s0})
        except IndexError as e:
            trace_error.print()
            error_msg = "Order is not created for this booking."
            _set_error(booking, error_msg)
            return JsonResponse({"message": error_msg})
    except SyntaxError:
        trace_error.print()
        return JsonResponse({"message": "Booking id is required"})


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def pod(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        _fp_name = fp_name.lower()
    except SyntaxError:
        trace_error.print()
        return JsonResponse(
            {"message": "Booking id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        booking = Bookings.objects.get(id=booking_id)
    except KeyError as e:
        trace_error.print()
        return JsonResponse({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = get_pod_payload(booking, fp_name)
        logger.info(f"### Payload ({fp_name} POD): {payload}")

        url = DME_LEVEL_API_URL + "/pod/fetchpod"
        response = requests.post(url, params={}, json=payload)
        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### Response ({fp_name} POD): {s0}")

        if _fp_name in ["hunter"]:
            try:
                podData = json_data[0]["podImage"]
            except KeyError as e:
                error_msg = json_data["errorMessage"]
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg})
        else:
            if "errorMessage" in json_data:
                error_msg = json_data["errorMessage"]
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg})
            elif "podData" not in json_data["pod"]:
                error_msg = "Unknown error, please contact support center."
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg})
            podData = json_data["pod"]["podData"]

        file_name = f"POD_{booking.pu_Address_State}_{booking.b_client_sales_inv_num}_{str(datetime.now().strftime('%Y%m%d_%H%M%S'))}"

        file_name += ".jpeg" if _fp_name in ["hunter"] else ".png"

        if IS_PRODUCTION:
            file_url = f"/opt/s3_public/imgs/{_fp_name}_au/{file_name}"
        else:
            file_url = f"./static/imgs/{file_name}"

        create_dir_if_not_exist(f"./static/pdfs/{_fp_name}_au")
        f = open(file_url, "wb")
        f.write(base64.b64decode(podData))
        f.close()

        booking.z_pod_url = f"{_fp_name}_au/{file_name}"
        booking.b_error_Capture = None
        booking.save()

        # POD Email
        if booking.b_send_POD_eMail:
            email_template_name = "POD"
            send_booking_status_email(
                booking.pk, email_template_name, request.user.username
            )

        return JsonResponse({"message": "POD is fetched successfully."})
    except Exception as e:
        trace_error.print()
        error_msg = f"KeyError: {e}"
        _set_error(booking, error_msg)
        return JsonResponse({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def reprint(request, fp_name):
    try:
        _fp_name = fp_name.lower()
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]

        try:
            booking = Bookings.objects.get(id=booking_id)
            payload = get_reprint_payload(booking, fp_name)

            logger.info(f"### Payload ({fp_name} REPRINT): {payload}")
            url = DME_LEVEL_API_URL + "/labelling/reprint"
            response = requests.post(url, params={}, json=payload)

            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)

            # s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
            # logger.info(f"### Response ({fp_name} POD): {s0}")

            podData = json_data["ReprintActionResult"]["LabelPDF"]

            try:
                file_name = f"{fp_name}_reprint_{booking.pu_Address_State}_{booking.b_client_sales_inv_num}_{str(datetime.now())}.pdf"

                if IS_PRODUCTION:
                    file_url = f"/opt/s3_public/pdfs/{_fp_name}_au/{file_name}"
                else:
                    file_url = f"./static/pdfs/{_fp_name}_au/{file_name}"

                create_dir_if_not_exist(f"./static/pdfs/{_fp_name}_au")
                with open(file_url, "wb") as f:
                    f.write(base64.b64decode(podData))
                    f.close()

                booking.z_label_url = file_url
                booking.b_error_Capture = None
                booking.save()

                return JsonResponse({"message": "Label is reprinted successfully."})
            except KeyError as e:
                trace_error.print()
                error_msg = f"KeyError: {e}"
                _set_error(booking, error_msg)
                return JsonResponse({"message": s0}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            if "errorMessage" in json_data:
                error_msg = json_data["errorMessage"]
                _set_error(booking, error_msg)
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )
            trace_error.print()
            return JsonResponse(
                {"Error": "Too many request"}, status=status.HTTP_400_BAD_REQUEST
            )
    except SyntaxError:
        trace_error.print()
        return JsonResponse(
            {"message": "Booking id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def pricing(request):
    body = literal_eval(request.body.decode("utf8"))
    booking_id = body["booking_id"]
    auto_select_type = body.get("auto_select_type", 1)
    is_pricing_only = False

    if not booking_id and "booking" in body:
        is_pricing_only = True

    booking, success, message, results = get_pricing(body, booking_id, is_pricing_only)

    if not success:
        return JsonResponse(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )
    else:
        json_results = ApiBookingQuotesSerializer(
            results, many=True, context={"booking": booking}
        ).data

        if is_pricing_only:
            API_booking_quotes.objects.filter(
                fk_booking_id=booking.pk_booking_id
            ).delete()
        else:
            auto_select_pricing(booking, results, auto_select_type)

        return JsonResponse(
            {"success": True, "message": message, "results": json_results},
            status=status.HTTP_200_OK,
        )


def get_pricing(body, booking_id, is_pricing_only=False):
    """
    @params:
        * is_pricing_only: only get pricing info
    """
    booking_lines = []
    booking = None

    # Only quote
    if is_pricing_only and not booking_id:
        booking = Struct(**body["booking"])

        for booking_line in body["booking_lines"]:
            booking_lines.append(Struct(**booking_line))

    if not is_pricing_only:
        booking = Bookings.objects.filter(id=booking_id).first()

        # Delete all pricing info if exist for this booking
        if booking:
            pk_booking_id = booking.pk_booking_id
            booking.api_booking_quote = None  # Reset pricing relation
            booking.save()
            # API_booking_quotes.objects.filter(fk_booking_id=pk_booking_id).delete()
            DME_Error.objects.filter(fk_booking_id=pk_booking_id).delete()
        else:
            return False, "Booking does not exist", None

    if not booking.puPickUpAvailFrom_Date:
        error_msg = "PU Available From Date is required."

        if not is_pricing_only:
            _set_error(booking, error_msg)

        return False, error_msg, None

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _pricing_process(booking, booking_lines, is_pricing_only)
        )
    finally:
        loop.close()

    results = API_booking_quotes.objects.filter(fk_booking_id=booking.pk_booking_id)
    return booking, True, "Retrieved all Pricing info", results


async def _pricing_process(booking, booking_lines, is_pricing_only):
    try:
        await asyncio.wait_for(
            pricing_workers(booking, booking_lines, is_pricing_only),
            timeout=PRICING_TIME,
        )
    except asyncio.TimeoutError:
        logger.info(f"#990 - {PRICING_TIME}s Timeout! stop threads! :)")


async def pricing_workers(booking, booking_lines, is_pricing_only):
    # Schedule n pricing works *concurrently*:
    _workers = set()
    logger.info("#910 - Building Pricing workers...")

    for fp_name in AVAILABLE_FPS_4_FC:
        _fp_name = fp_name.lower()

        if _fp_name not in FP_CREDENTIALS and _fp_name not in BUILT_IN_PRICINGS:
            continue

        if _fp_name in FP_CREDENTIALS:
            fp_client_names = FP_CREDENTIALS[_fp_name].keys()
            b_client_name = booking.b_client_name.lower()

            for client_name in fp_client_names:
                if b_client_name in fp_client_names and b_client_name != client_name:
                    continue
                elif (
                    b_client_name not in fp_client_names
                    and client_name not in ["dme", "test"]
                    and not is_pricing_only
                ):
                    continue

                logger.info(f"#905 INFO Pricing - {_fp_name}, {client_name}")
                for key in FP_CREDENTIALS[_fp_name][client_name].keys():
                    account_detail = FP_CREDENTIALS[_fp_name][client_name][key]

                    # Allow live pricing credentials only on PROD
                    if settings.ENV == "prod" and "test" in key:
                        continue

                    # Pricing only accounts can be used on pricing_only mode
                    if "pricingOnly" in account_detail and not is_pricing_only:
                        continue

                    _worker = _api_pricing_worker_builder(
                        _fp_name,
                        booking,
                        booking_lines,
                        is_pricing_only,
                        account_detail,
                    )
                    _workers.add(_worker)
        # elif _fp_name in BUILT_IN_PRICINGS:
        #     _worker = _built_in_pricing_worker_builder(_fp_name, booking)
        #     _workers.add(_worker)

    logger.info("#911 - Pricing workers will start soon")
    await asyncio.gather(*_workers)
    logger.info("#919 - Pricing workers finished all")


async def _api_pricing_worker_builder(
    _fp_name, booking, booking_lines, is_pricing_only, account_detail
):
    payload = get_pricing_payload(booking, _fp_name, account_detail, booking_lines)

    if not payload:
        return None

    logger.info(f"### Payload ({_fp_name.upper()} PRICING): {payload}")
    url = DME_LEVEL_API_URL + "/pricing/calculateprice"
    logger.info(f"### API url ({_fp_name.upper()} PRICING): {url}")

    try:
        response = await requests_async.post(url, params={}, json=payload)
        logger.info(f"### Response ({_fp_name.upper()} PRICING): {response}")
        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### Response Detail ({_fp_name.upper()} PRICING): {s0}")

        if not is_pricing_only:
            Log.objects.create(
                request_payload=payload,
                request_status="SUCCESS",
                request_type=f"{_fp_name.upper()} PRICING",
                response=res_content,
                fk_booking_id=booking.id,
            )

        # error = capture_errors(
        #     response,
        #     booking,
        #     _fp_name,
        #     payload["spAccountDetails"]["accountCode"],
        # )

        parse_results = parse_pricing_response(response, _fp_name, booking)

        if parse_results and not "error" in parse_results:
            for parse_result in parse_results:
                parse_result["account_code"] = payload["spAccountDetails"][
                    "accountCode"
                ]

                quotes = API_booking_quotes.objects.filter(
                    fk_booking_id=booking.pk_booking_id,
                    freight_provider__iexact=parse_result["freight_provider"],
                    service_name=parse_result["service_name"],
                    account_code=payload["spAccountDetails"]["accountCode"],
                )

                if quotes.exists():
                    serializer = ApiBookingQuotesSerializer(
                        quotes[0], data=parse_result
                    )
                else:
                    serializer = ApiBookingQuotesSerializer(data=parse_result)

                if serializer.is_valid():
                    serializer.save()
                else:
                    logger.info(f"@401 Serializer error: {serializer.errors}")
    except Exception as e:
        trace_error.print()
        logger.info(f"@402 Exception: {e}")


async def _built_in_pricing_worker_builder(_fp_name, booking):
    results = get_pricing(_fp_name, booking)
    parse_results = parse_pricing_response(results, _fp_name, booking, True)

    for parse_result in parse_results:
        quotes = API_booking_quotes.objects.filter(
            fk_booking_id=booking.pk_booking_id,
            freight_provider__iexact=parse_result["freight_provider"],
            service_name=parse_result["service_name"],
        )

        if quotes.exists():
            serializer = ApiBookingQuotesSerializer(quotes[0], data=parse_result)
        else:
            serializer = ApiBookingQuotesSerializer(data=parse_result)

        if serializer.is_valid():
            serializer.save()
        else:
            logger.info(f"@404 Serializer error: {serializer.errors}")
