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
from api.file_operations.directory import create_dir
from api.file_operations.downloads import download_from_url
from api.utils import get_eta_pu_by, get_eta_de_by
from api.operations.email_senders import send_booking_status_email
from api.operations.labels.index import build_label

from api.fp_apis.payload_builder import *
from api.fp_apis.response_parser import *
from api.fp_apis.pre_check import *
from api.fp_apis.operations.common import _set_error
from api.fp_apis.operations.tracking import update_booking_with_tracking_result
from api.fp_apis.operations.book import book as book_oper
from api.fp_apis.operations.pricing import pricing as pricing_oper
from api.fp_apis.utils import (
    get_dme_status_from_fp_status,
    auto_select_pricing,
)
from api.fp_apis.constants import S3_URL, DME_LEVEL_API_URL


logger = logging.getLogger("dme_api")


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def tracking(request, fp_name):
    body = literal_eval(request.body.decode("utf8"))
    booking_id = body["booking_id"]

    try:
        booking = Bookings.objects.get(id=booking_id)
        payload = get_tracking_payload(booking, fp_name)

        log = Log(
            request_payload=payload,
            request_status="SUCCESS",
            request_type=f"{fp_name.upper()} TRACKING",
            response={},
            fk_booking_id=booking.id,
        )

        logger.info(f"### Payload ({fp_name} tracking): {payload}")
        url = DME_LEVEL_API_URL + "/tracking/trackconsignment"
        response = requests.post(url, params={}, json=payload)

        if fp_name.lower() in ["tnt"]:
            res_content = response.content.decode("utf8")
        else:
            res_content = response.content.decode("utf8").replace("'", '"')

        log.response = res_content

        json_data = json.loads(res_content)
        s0 = json.dumps(json_data, indent=2, sort_keys=True)  # Just for visual
        # Disabled on 2021-02-05
        # logger.info(f"### Response ({fp_name} tracking): {s0}")

        try:
            log.save()

            consignmentTrackDetails = json_data["consignmentTrackDetails"][0]
            consignmentStatuses = consignmentTrackDetails["consignmentStatuses"]
            update_booking_with_tracking_result(
                request, booking, fp_name, consignmentStatuses
            )
            booking.b_error_Capture = None
            booking.save()

            return JsonResponse(
                {
                    "message": f"DME status: {booking.b_status}, FP status: {booking.b_status_API}",
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
        logger.error(f"#511 ERROR: {e}")
        return JsonResponse(
            {"message": "Booking not found"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        trace_error.print()
        logger.error(f"#512 ERROR: {e}")
        return JsonResponse(
            {"message": "Tracking failed"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def book(request, fp_name):
    try:
        username = request.user.username
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
    except SyntaxError as e:
        trace_error.print()
        logger.error(f"#514 BOOK error: {error_msg}")
        return JsonResponse(
            {"message": f"SyntaxError: {e}"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        booking = Bookings.objects.get(id=booking_id)
        success, message = book_oper(fp_name, booking, username)
        res_json = {"success": success, "message": message}

        if success:
            return JsonResponse(res_json)
        else:
            return JsonResponse(res_json, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        trace_error.print()
        error_msg = str(e)
        logger.error(f"#513 BOOK error: {error_msg}")
        _set_error(booking, error_msg)
        return JsonResponse({"message": error_msg}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def rebook(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        _fp_name = fp_name.lower()

        try:
            booking = Bookings.objects.get(id=booking_id)

            error_msg = pre_check_rebook(booking)

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

            logger.info(f"### Payload ({fp_name} rebook): {payload}")
            url = DME_LEVEL_API_URL + "/booking/rebookconsignment"
            response = requests.post(url, params={}, json=payload)
            res_content = response.content.decode("utf8").replace("'", '"')
            json_data = json.loads(res_content)
            s0 = json.dumps(
                json_data, indent=2, sort_keys=True, default=str
            )  # Just for visual
            logger.info(f"### Response ({fp_name} rebook): {s0}")

            log = Log(
                request_payload=payload,
                request_status="",
                request_type=f"{fp_name.upper()} REBOOK",
                response=res_content,
                fk_booking_id=booking.id,
            )

            if response.status_code == 200:
                try:
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

                    log.request_status = "SUCCESS"
                    log.save()

                    return JsonResponse(
                        {"message": f"Successfully booked({booking.v_FPBookingNumber})"}
                    )
                except KeyError as e:
                    trace_error.print()
                    log.request_status = "ERROR"
                    log.save()

                    error_msg = s0
                    _set_error(booking, error_msg)
                    return JsonResponse(
                        {"message": error_msg}, status=status.HTTP_400_BAD_REQUEST
                    )
            elif response.status_code == 400:
                log.request_status = "ERROR"
                log.save()

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
                log.request_status = "ERROR"
                log.save()

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

            request_type = f"{fp_name.upper()} EDIT BOOK"
            log = Log(
                request_payload=payload,
                request_status="",
                request_type=request_type,
                response=res_content,
                fk_booking_id=booking.id,
            )

            try:
                booking.v_FPBookingNumber = json_data["items"][0]["tracking_details"][
                    "consignment_id"
                ]
                booking.fk_fp_pickup_id = json_data["consignmentNumber"]
                booking.b_dateBookedDate = datetime.now()
                booking.b_status = "Booked"
                booking.b_error_Capture = None
                booking.save()

                log.request_status = "SUCCESS"
                log.save()

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

                log.request_status = "ERROR"
                log.save()

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

                log = Log(
                    request_payload=payload,
                    request_status="",
                    request_type=f"{fp_name.upper()} CANCEL BOOK",
                    response=res_content,
                    fk_booking_id=booking.id,
                )

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

                        log.request_status = "SUCCESS"
                        log.save()

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
                    
                    log.request_status = "ERROR"
                    log.save()

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

        log = Log(
            request_payload={},
            request_status="",
            request_type="",
            response={},
            fk_booking_id=booking.id,
        )

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
                
                log.request_payload=payload,
                log.request_status=request_status,
                log.request_type=request_type,
                log.response=res_content,
                log.save()

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
                        and _fp_name in ["startrack", "auspost"]
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

                if _fp_name in ["startrack", "auspost"]:
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
                        full_path = f"{S3_URL}/pdfs/{z_label_url}"

                        if _fp_name == "tnt":
                            with open(full_path, "wb") as f:
                                f.write(label_data)
                                f.close()
                        else:
                            pdf_url = json_data["pdfURL"]
                            download_from_url(pdf_url, full_path)
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
                    file_path = f"{S3_URL}/pdfs/{_fp_name}_au/"
                    file_path, file_name = build_label(booking, file_path)
                    z_label_url = f"{_fp_name}_au/{file_name}"

                booking.z_label_url = z_label_url
                booking.b_error_Capture = None
                booking.save()

                # Do not send email when booking is `Rebooked`
                if (
                    not _fp_name in ["startrack", "auspost"]
                    and not "Rebooked" in booking.b_status
                ):
                    # Send email when GET_LABEL
                    email_template_name = "General Booking"

                    if booking.b_booking_Category == "Salvage Expense":
                        email_template_name = "Return Booking"

                    send_booking_status_email(
                        booking.pk, email_template_name, request.user.username
                    )

                # if not _fp_name in ["sendle"]:
                log.request_payload=payload,
                log.request_status="SUCCESS",
                log.request_type=f"{fp_name.upper()} GET LABEL",
                log.response=res_content,
                log.save()

                return JsonResponse(
                    {"message": f"Successfully created label({booking.z_label_url})"},
                    status=status.HTTP_200_OK,
                )
            except KeyError as e:
                logger.error(f"[GET LABEL] Error - {str(e)}")
                trace_error.print()

                log.request_payload=payload,
                log.request_status="SUCCESS",
                log.request_type=f"{fp_name.upper()} GET LABEL",
                log.response=res_content,
                log.save()

                error_msg = res_content

                if _fp_name in ["tnt"]:
                    error_msg = res_content

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

        log = Log(
            request_payload=payload,
            request_status="",
            request_type=f"{fp_name.upper()} CREATE ORDER",
            response=res_content,
            fk_booking_id="",
        )

        try:
            log.request_status="SUCCESS",
            log.fk_booking_id=bookings[0].pk_booking_id,
            log.save()

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

            log.request_status="ERROR",
            log.fk_booking_id=booking.id,
            log.save()

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

            log = Log(
                request_payload=payload,
                request_status="",
                request_type=f"{fp_name} GET ORDER SUMMARY",
                response=res_content,
                fk_booking_id="",
            )

            try:
                file_name = f"biopak_manifest_{str(booking.vx_fp_order_id)}_{str(datetime.now())}.pdf"
                full_path = f"{S3_URL}/pdfs/{_fp_name}_au/{file_name}"

                with open(full_path, "wb") as f:
                    f.write(bytes(json_data["pdfData"]["data"]))
                    f.close()

                bookings = Bookings.objects.filter(pk__in=booking_ids)

                manifest_timestamp = datetime.now()
                for booking in bookings:
                    booking.z_manifest_url = f"{_fp_name}_au/{file_name}"
                    booking.manifest_timestamp = manifest_timestamp
                    booking.save()

                log.request_status="SUCCESS",
                log.fk_booking_id=bookings[0].pk_booking_id,
                log.save()

                return JsonResponse({"message": "Manifest is created successfully."})
            except KeyError as e:
                trace_error.print()
                
                log.request_status="FAILED",
                log.fk_booking_id=bookings[0].pk_booking_id,
                log.save()

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
        full_path = f"{S3_URL}/imgs/{_fp_name}_au/{file_name}"

        f = open(full_path, "wb")
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
                full_path = f"{S3_URL}/pdfs/{_fp_name}_au/{file_name}"

                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(podData))
                    f.close()

                booking.z_label_url = f"{_fp_name}_au/{file_name}"
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

    booking, success, message, results = pricing_oper(body, booking_id, is_pricing_only)

    if not success:
        return JsonResponse(
            {"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST
        )

    json_results = ApiBookingQuotesSerializer(
        results, many=True, context={"booking": booking}
    ).data

    if is_pricing_only:
        API_booking_quotes.objects.filter(fk_booking_id=booking.pk_booking_id).delete()
    else:
        auto_select_pricing(booking, results, auto_select_type)

    res_json = {"success": True, "message": message, "results": json_results}
    return JsonResponse(res_json, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def update_servce_code(request, fp_name):
    _fp_name = fp_name.lower()

    try:
        payload = get_get_accounts_payload(_fp_name)
        headers = {"Accept": "application/pdf", "Content-Type": "application/json"}
        logger.info(f"### Payload ({fp_name.upper()} Get Accounts): {payload}")
        url = DME_LEVEL_API_URL + "/servicecode/getaccounts"
        response = requests.post(url, json=payload, headers=headers)
        res_content = response.content
        json_data = json.loads(res_content)
        # Just for visual
        s0 = json.dumps(json_data, indent=2, sort_keys=True, default=str)
        fp = Fp_freight_providers.objects.filter(
            fp_company_name__iexact=_fp_name
        ).first()

        for data in json_data["returns_products"]:
            product_type = data["type"]
            product_id = data["product_id"]

            etd, is_created = FP_Service_ETDs.objects.update_or_create(
                fp_delivery_service_code=product_id,
                fp_delivery_time_description=product_type,
                freight_provider=fp,
                dme_service_code_id=1,
            )

        for data in json_data["postage_products"]:
            product_type = data["type"]
            product_id = data["product_id"]

            etd, is_created = FP_Service_ETDs.objects.update_or_create(
                fp_delivery_service_code=product_id,
                fp_delivery_time_description=product_type,
                freight_provider=fp,
                dme_service_code_id=1,
            )

        return JsonResponse({"message": "Updated service codes successfully."})
    except IndexError as e:
        trace_error.print()
        error_msg = "GetAccounts is failed."
        _set_error(booking, error_msg)
        return JsonResponse({"message": error_msg})
