import time as t
import json
import requests
import datetime
import base64
import os
import logging
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
from api.outputs import emails as email_module

from .payload_builder import *
from .self_pricing import get_pricing as get_self_pricing
from .utils import (
    get_dme_status_from_fp_status,
    get_account_code_key,
    auto_select_pricing,
)
from .response_parser import *
from .pre_check import *
from .update_by_json import update_biopak_with_booked_booking
from .build_label.dhl import build_dhl_label
from .operations.tracking import update_booking_with_tracking_result

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
        if fp_name.lower() in ["hunter"]:
            account_code_key = get_account_code_key(booking, fp_name)

            if not account_code_key:
                logger.info(f"#501 ERROR: {booking.b_error_Capture}")
                return JsonResponse(
                    {"message": booking.b_error_Capture},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = get_tracking_payload(booking, fp_name, account_code_key)
        else:
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

            return JsonResponse(
                {
                    "message": f"DME status: {booking.b_status},FP status: {booking.b_status_API}",
                    "b_status": booking.b_status,
                    "b_status_API": booking.b_status_API,
                },
                status=status.HTTP_200_OK,
            )
        except KeyError:
            trace_error.print()

            if "errorMessage" in json_data:
                error_msg = json_data["errorMessage"]
                _set_error(booking, error_msg)
                logger.info(f"#510 ERROR: {error_msg}")
                return JsonResponse(
                    {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                )

            return JsonResponse(
                {"error": "Failed Tracking"}, status=status.HTTP_400_BAD_REQUEST
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

        try:
            booking = Bookings.objects.get(id=booking_id)
            error_msg = pre_check_book(booking)

            if error_msg:
                return JsonResponse(
                    {"message": f"#700 Error: {error_msg}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                if fp_name.lower() in ["hunter"]:
                    account_code_key = get_account_code_key(booking, fp_name)

                    if not account_code_key:
                        return JsonResponse(
                            {"message": f"#701 Error: {booking.b_error_Capture}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    payload = get_book_payload(booking, fp_name, account_code_key)
                else:
                    payload = get_book_payload(booking, fp_name)
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
                and fp_name.lower() == "startrack"
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
                    status_history.create(booking, "Booked", request.user.username)
                    booking.b_status = "Booked"
                    booking.b_error_Capture = ""
                    booking.save()

                    Log(
                        request_payload=request_payload,
                        request_status="SUCCESS",
                        request_type=f"{fp_name.upper()} BOOK",
                        response=res_content,
                        fk_booking_id=booking.id,
                    ).save()

                    # Save Label for Hunter
                    create_dir_if_not_exist(f"./static/pdfs/{fp_name.lower()}_au")
                    if booking.vx_freight_provider.lower() == "hunter":
                        json_label_data = json.loads(response.content)
                        file_name = f"hunter_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"

                        if IS_PRODUCTION:
                            file_url = (
                                f"/opt/s3_public/pdfs/{fp_name.lower()}_au/{file_name}"
                            )
                        else:
                            file_url = f"./static/pdfs/{fp_name.lower()}_au/{file_name}"

                        with open(file_url, "wb") as f:
                            f.write(base64.b64decode(json_label_data["shippingLabel"]))
                            f.close()
                            booking.z_label_url = f"hunter_au/{file_name}"
                            booking.save()

                            # Send email when GET_LABEL
                            email_template_name = "General Booking"

                            if booking.b_booking_Category == "Salvage Expense":
                                email_template_name = "Return Booking"

                            email_module.send_booking_email_using_template(
                                booking.pk, email_template_name, request.user.username
                            )
                    # Save Label for Capital
                    elif booking.vx_freight_provider.lower() == "capital":
                        json_label_data = json.loads(response.content)
                        file_name = f"capital_{str(booking.v_FPBookingNumber)}_{str(datetime.now())}.pdf"

                        if IS_PRODUCTION:
                            file_url = (
                                f"/opt/s3_public/pdfs/{fp_name.lower()}_au/{file_name}"
                            )
                        else:
                            file_url = f"./static/pdfs/{fp_name.lower()}_au/{file_name}"

                        with open(file_url, "wb") as f:
                            f.write(base64.b64decode(json_label_data["Label"]))
                            f.close()
                            booking.z_label_url = f"capital_au/{file_name}"
                            booking.save()

                            # Send email when GET_LABEL
                            email_template_name = "General Booking"

                            if booking.b_booking_Category == "Salvage Expense":
                                email_template_name = "Return Booking"

                            email_module.send_booking_email_using_template(
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
                booking.b_error_Capture = ""
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

        error_msg = pre_check_label(booking)

        if error_msg:
            return JsonResponse(
                {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
            )

        payload = {}
        if fp_name.lower() in ["startrack"]:
            try:
                payload = get_create_label_payload(booking, fp_name)

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
        elif fp_name.lower() in ["tnt", "sendle"]:
            payload = get_getlabel_payload(booking, fp_name)
        try:
            logger.info(f"### Payload ({fp_name} get_label): {payload}")
            url = DME_LEVEL_API_URL + "/labelling/getlabel"
            json_data = None

            while (
                json_data is None
                or (
                    json_data is not None
                    and fp_name.lower() == "startrack"
                    and json_data["labels"][0]["status"] == "PENDING"
                )
                or (
                    json_data is not None
                    and fp_name.lower() == "tnt"
                    and json_data["anyType"]["Status"] != "SUCCESS"
                )
            ):
                t.sleep(5)  # Delay to wait label is created
                response = requests.post(url, params={}, json=payload)
                res_content = response.content.decode("utf8").replace("'", '"')

                if fp_name.lower() in ["sendle"]:
                    res_content = response.content.decode("utf8")

                json_data = json.loads(res_content)
                s0 = json.dumps(
                    json_data, indent=2, sort_keys=True, default=str
                )  # Just for visual
                logger.info(f"### Response ({fp_name} get_label): {s0}")

            if fp_name.lower() in ["startrack"]:
                z_label_url = download_external.pdf(
                    json_data["labels"][0]["url"], booking
                )
            elif fp_name.lower() in ["tnt", "sendle"]:
                try:
                    if fp_name.lower() == "tnt":
                        label_data = base64.b64decode(json_data["anyType"]["LabelPDF"])
                        file_name = f"{fp_name}_label_{booking.pu_Address_State}_{booking.b_client_sales_inv_num}_{str(datetime.now())}.pdf"
                    elif fp_name.lower() == "sendle":
                        file_name = f"{fp_name}_label_{booking.pu_Address_State}_{booking.v_FPBookingNumber}_{str(datetime.now())}.pdf"

                    z_label_url = f"{fp_name.lower()}_au/{file_name}"

                    if settings.ENV == "prod":
                        label_url = f"/opt/s3_public/pdfs/{z_label_url}"
                    else:
                        label_url = f"./static/pdfs/{z_label_url}"

                    create_dir_if_not_exist(f"./static/pdfs/{fp_name.lower()}_au")

                    if fp_name.lower() == "tnt":
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

            elif fp_name.lower() in ["dhl"]:
                z_label_url = build_dhl_label(booking)

            booking.z_label_url = z_label_url
            booking.save()

            if not fp_name.lower() in ["startrack"]:
                # Send email when GET_LABEL
                email_template_name = "General Booking"

                if booking.b_booking_Category == "Salvage Expense":
                    email_template_name = "Return Booking"

                email_module.send_booking_email_using_template(
                    booking.pk, email_template_name, request.user.username
                )

            if not fp_name.lower() in ["sendle"]:
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

            if fp_name.lower() in ["tnt"]:
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
                    file_url = f"/opt/s3_public/pdfs/{fp_name.lower()}_au/{file_name}"
                else:
                    file_url = f"./static/pdfs/{fp_name.lower()}_au/{file_name}"

                create_dir_if_not_exist(f"./static/pdfs/{fp_name.lower()}_au")
                with open(file_url, "wb") as f:
                    f.write(bytes(json_data["pdfData"]["data"]))
                    f.close()

                bookings = Bookings.objects.filter(pk__in=booking_ids)

                manifest_timestamp = datetime.now()
                for booking in bookings:
                    booking.z_manifest_url = f"{fp_name.lower()}_au/{file_name}"
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
        if fp_name.lower() in ["hunter"]:
            account_code_key = get_account_code_key(booking, fp_name)

            if not account_code_key:
                return JsonResponse(
                    {"message": booking.b_error_Capture},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = get_pod_payload(booking, fp_name, account_code_key)
        else:
            payload = get_pod_payload(booking, fp_name)

        logger.info(f"### Payload ({fp_name} POD): {payload}")
        url = DME_LEVEL_API_URL + "/pod/fetchpod"
        response = requests.post(url, params={}, json=payload)
        res_content = response.content.decode("utf8").replace("'", '"')
        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        logger.info(f"### Response ({fp_name} POD): {s0}")

        if fp_name.lower() in ["hunter"]:
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

        file_name += ".jpeg" if fp_name.lower() in ["hunter"] else ".png"

        if IS_PRODUCTION:
            file_url = f"/opt/s3_public/imgs/{fp_name.lower()}_au/{file_name}"
        else:
            file_url = f"./static/imgs/{file_name}"

        create_dir_if_not_exist(f"./static/pdfs/{fp_name.lower()}_au")
        f = open(file_url, "wb")
        f.write(base64.b64decode(podData))
        f.close()

        booking.z_pod_url = f"{fp_name.lower()}_au/{file_name}"
        booking.save()

        # POD Email
        if booking.b_send_POD_eMail:
            email_template_name = "POD"
            email_module.send_booking_email_using_template(
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
                    file_url = f"/opt/s3_public/pdfs/{fp_name.lower()}_au/{file_name}"
                else:
                    file_url = f"./static/pdfs/{fp_name.lower()}_au/{file_name}"

                create_dir_if_not_exist(f"./static/pdfs/{fp_name.lower()}_au")
                with open(file_url, "wb") as f:
                    f.write(base64.b64decode(podData))
                    f.close()

                booking.z_label_url = file_url
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

    success, message, results = get_pricing(
        body, booking_id, auto_select_type, is_pricing_only
    )

    if not success:
        return JsonResponse(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )
    else:
        if is_pricing_only:
            API_booking_quotes.objects.filter(
                fk_booking_id=booking.pk_booking_id
            ).delete()
        else:
            auto_select_pricing(booking, results, auto_select_type)

        results = ApiBookingQuotesSerializer(results, many=True).data
        return JsonResponse(
            {"success": True, "message": message}, status=status.HTTP_200_OK
        )


def get_pricing(body, booking_id, is_pricing_only):
    booking_lines = []
    booking = None

    # Only quote
    if is_pricing_only and not booking_id:
        booking = Struct(**body["booking"])
        client_warehouse_code = booking.client_warehouse_code

        for booking_line in body["booking_lines"]:
            booking_lines.append(Struct(**booking_line))

    if not is_pricing_only:
        try:
            booking = Bookings.objects.get(id=booking_id)
            client_warehouse_code = booking.fk_client_warehouse.client_warehouse_code

            if booking:  # Delete all pricing info if exist for this booking
                booking.api_booking_quote = None  # Reset pricing relation
                booking.save()
                API_booking_quotes.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                ).delete()
        except Exception as e:
            trace_error.print()
            return False, "Booking is not exist", None

    if not booking.puPickUpAvailFrom_Date:
        error_msg = "PU Available From Date is required."

        if not is_pricing_only:
            _set_error(booking, error_msg)

        return False, error_msg, None

    #       "Startrack"
    #       "Camerons",
    #       "Toll",
    #       "Sendle"
    # fp_names = ["TNT", "Hunter", "Capital", "Century", "Fastway"]
    fp_names = ["Hunter"]
    DME_Error.objects.filter(fk_booking_id=booking.pk_booking_id).delete()

    try:
        for fp_name in fp_names:
            if (
                fp_name.lower() not in ACCOUNT_CODES
                and fp_name.lower() not in BUILT_IN_PRICINGS
            ):
                return False, "Not supported FP", None
            elif fp_name.lower() in ACCOUNT_CODES:
                for account_code_key in ACCOUNT_CODES[fp_name.lower()]:
                    logger.info(
                        f"#905 INFO Pricing - {fp_name.lower()}, {account_code_key}"
                    )

                    # Allow live pricing credentials only on PROD
                    if settings.ENV == "prod" and "test" in account_code_key:
                        continue

                    if (
                        "SWYTEMPBUN" in client_warehouse_code
                        and not "bunnings" in account_code_key
                    ):
                        continue
                    elif (
                        not "SWYTEMPBUN" in client_warehouse_code
                        and "bunnings" in account_code_key
                    ):
                        continue

                    payload = get_pricing_payload(
                        booking, fp_name.lower(), account_code_key, booking_lines
                    )

                    if not payload:
                        continue

                    logger.info(f"### Payload ({fp_name.upper()} PRICING): {payload}")
                    url = DME_LEVEL_API_URL + "/pricing/calculateprice"
                    logger.info(f"### API url ({fp_name.upper()} PRICING): {url}")

                    try:
                        response = requests.post(url, params={}, json=payload)
                        logger.info(
                            f"### Response ({fp_name.upper()} PRICING): {response}"
                        )

                        res_content = response.content.decode("utf8").replace("'", '"')
                        json_data = json.loads(res_content)
                        s0 = json.dumps(
                            json_data, indent=2, sort_keys=True
                        )  # Just for visual
                        logger.info(
                            f"### Response Detail ({fp_name.upper()} PRICING): {s0}"
                        )

                        if not is_pricing_only:
                            Log.objects.create(
                                request_payload=payload,
                                request_status="SUCCESS",
                                request_type=f"{fp_name.upper()} PRICING",
                                response=res_content,
                                fk_booking_id=booking.id,
                            )

                        error = capture_errors(
                            response,
                            booking,
                            fp_name.lower(),
                            payload["spAccountDetails"]["accountCode"],
                        )

                        parse_results = parse_pricing_response(
                            response, fp_name.lower(), booking
                        )

                        if parse_results and not "error" in parse_results:
                            for parse_result in parse_results:
                                parse_result["account_code"] = payload[
                                    "spAccountDetails"
                                ]["accountCode"]

                                try:
                                    api_booking_quote = API_booking_quotes.objects.get(
                                        fk_booking_id=booking.pk_booking_id,
                                        fk_freight_provider_id=parse_result[
                                            "fk_freight_provider_id"
                                        ].upper(),
                                        service_name=parse_result["service_name"],
                                        account_code=payload["spAccountDetails"][
                                            "accountCode"
                                        ],
                                    )
                                    serializer = ApiBookingQuotesSerializer(
                                        api_booking_quote, data=parse_result
                                    )

                                    try:
                                        if serializer.is_valid():
                                            serializer.save()
                                    except Exception as e:
                                        trace_error.print()
                                        logger.info("Exception: ", e)

                                    api_booking_quote.save()
                                except API_booking_quotes.DoesNotExist as e:
                                    trace_error.print()
                                    serializer = ApiBookingQuotesSerializer(
                                        data=parse_result
                                    )

                                    if serializer.is_valid():
                                        serializer.save()
                                    else:
                                        logger.info(
                                            f"@401 Serializer error: {serializer.errors}"
                                        )

                    except Exception as e:
                        trace_error.print()
                        logger.info(f"@402 Exception: {e}")

            elif fp_name.lower() in BUILT_IN_PRICINGS:
                results = get_self_pricing(fp_name.lower(), booking)
                parse_results = parse_pricing_response(
                    results, fp_name.lower(), booking, True
                )

                for parse_result in parse_results:
                    try:
                        api_booking_quote = API_booking_quotes.objects.get(
                            fk_booking_id=booking.pk_booking_id,
                            fk_freight_provider_id=parse_result[
                                "fk_freight_provider_id"
                            ].upper(),
                            service_name=parse_result["service_name"],
                        )

                        serializer = ApiBookingQuotesSerializer(
                            api_booking_quote, data=parse_result
                        )
                        if serializer.is_valid():
                            serializer.save()
                        else:
                            logger.info(f"@403 Serializer error: {serializer.errors}")

                        api_booking_quote.save()
                    except API_booking_quotes.DoesNotExist as e:
                        trace_error.print()
                        serializer = ApiBookingQuotesSerializer(data=parse_result)

                        try:
                            if serializer.is_valid():
                                serializer.save()
                            else:
                                logger.info(
                                    f"@404 Serializer error: {serializer.errors}"
                                )
                        except Exception as e:
                            trace_error.print()
                            logger.info(f"@405 Exception: {e}")

        results = API_booking_quotes.objects.filter(fk_booking_id=booking.pk_booking_id)
        return True, "Retrieved all Pricing info", results
    except Exception as e:
        trace_error.print()
        return False, f"Error: {e}", None
