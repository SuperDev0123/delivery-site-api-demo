import time, json, requests, datetime, base64, os
from ast import literal_eval

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse

from api.models import *
from django.conf import settings
from .payload_builder import *

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


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def tracking(request, fp_name):
    body = literal_eval(request.body.decode("utf8"))
    booking_id = body["booking_id"]

    try:
        booking = Bookings.objects.get(id=booking_id)
        payload = get_tracking_payload(booking, fp_name)

        # print(f'### Payload ({fp_name} tracking): {data}')
        url = DME_LEVEL_API_URL + "/tracking/trackconsignment"
        response0 = requests.post(url, params={}, json=payload)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True)  # Just for visual
        # print(f"### Response ({fp_name} tracking): {s0}")

        try:
            request_id = data0["requestId"]
            request_payload = {
                "apiUrl": "",
                "accountCode": "",
                "authKey": "",
                "trackingId": "",
            }
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = payload["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = payload["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = payload["consignmentDetails"][0][
                "consignmentNumber"
            ]
            request_type = f"{fp_name.upper()} TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(
                request_payload=request_payload,
                request_status=request_status,
                request_type=request_type,
                response=response0,
                fk_booking_id=booking.id,
            )
            oneLog.save()
            booking.b_status_API = data0["consignmentTrackDetails"][0][
                "consignmentStatuses"
            ][0]["status"]
            booking.save()

            return JsonResponse({"message": booking.b_status_API}, status=200)
        except KeyError:
            return JsonResponse({"Error": "Too many request"}, status=400)
    except Exception as e:
        return JsonResponse({"message": "Booking not found"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def book(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]

        try:
            booking = Bookings.objects.get(id=booking_id)

            if booking.b_status.lower() == "booked":
                return JsonResponse(
                    {"message": "Booking is already booked."}, status=400
                )

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                error_msg = "State for pickup postal address is required."
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg}, status=400)

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                error_msg = "Suburb name for pickup postal address is required."
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg}, status=400)

            try:
                payload = get_book_payload(booking, fp_name)
            except Exception as e:
                print(f"#401 - Error while build payload: {e}")
                return JsonResponse({"message": str(e)}, status=400)

            # print(f"### Payload ({fp_name} book): {payload}")
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=payload)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print(f"### Response ({fp_name} book): {s0}")

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
                request_payload["trackingId"] = data0["consignmentNumber"]
                request_type = f"{fp_name.upper()} BOOK"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0["consignment_id"]
                booking.fk_fp_pickup_id = data0["consignmentNumber"]
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.save()

                log = Log(
                    request_payload=request_payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                ).save()

                Api_booking_confirmation_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                ).delete()

                for item in data0["items"]:
                    book_con = Api_booking_confirmation_lines(
                        fk_booking_id=booking.pk_booking_id, api_item_id=item["item_id"]
                    ).save()

                return JsonResponse(
                    {"message": f"Successfully booked({booking.v_FPBookingNumber})"}
                )
            except KeyError:
                try:
                    log = Log(
                        request_payload=payload,
                        request_status="ERROR",
                        request_type=f"{fp_name.upper()} BOOK",
                        response=response0,
                        fk_booking_id=booking.id,
                    ).save()

                    error_msg = data0[0]["field"]
                    _set_error(booking, error_msg)
                    return JsonResponse({"message": error_msg}, status=400)
                except KeyError:
                    error_msg = data0
                    _set_error(booking, error_msg)
                    return JsonResponse({"message": s0}, status=400)
        except IndexError:
            return JsonResponse({"message": "Booking not found"}, status=400)
        except TypeError:
            error_msg = data0[0]["field"]
            _set_error(booking, error_msg)
            return JsonResponse({"message": error_msg}, status=400)
    except SyntaxError:
        return JsonResponse({"message": "Booking id is required"}, status=400)


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

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                error_msg = "Suburb name for pickup postal address is required."
                _set_error(booking, error_msg)
                return booking_id({"message": error_msg})

            payload = get_book_payload(booking, fp_name)

            # print(f"### Payload ({fp_name} edit book): {payload}")
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=payload)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print(f"### Response ({fp_name} edit book): {s0}")

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
                request_payload["trackingId"] = data0["consignmentNumber"]
                request_type = f"{fp_name.upper()} EDIT BOOK"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0["consignment_id"]
                booking.fk_fp_pickup_id = data0["consignmentNumber"]
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.save()

                oneLog = Log(
                    request_payload=request_payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                ).save()

                Api_booking_confirmation_lines.objects.filter(
                    fk_booking_id=booking.pk_booking_id
                ).delete()

                for item in data0["items"]:
                    book_con = Api_booking_confirmation_lines(
                        fk_booking_id=booking.pk_booking_id, api_item_id=item["item_id"]
                    ).save()

                return JsonResponse(
                    {"message": f"Successfully edit book({booking.v_FPBookingNumber})"}
                )
            except KeyError:
                try:
                    request_type = f"{fp_name.upper()} EDIT BOOK"
                    request_status = "ERROR"
                    oneLog = Log(
                        request_payload=payload,
                        request_status=request_status,
                        request_type=request_type,
                        response=response0,
                        fk_booking_id=booking.id,
                    )
                    oneLog.save()

                    error_msg = data0["errors"]
                    _set_error(booking, error_msg)
                    return JsonResponse({"message": error_msg}, status=400)
                except KeyError:
                    error_msg = data0
                    _set_error(booking, error_msg)
                    return JsonResponse({"message": s0}, status=400)
        except IndexError:
            return JsonResponse({"message": "Booking not found"}, status=400)
    except SyntaxError:
        return JsonResponse({"message": "Booking id is required"}, status=400)


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

                # print(f"### Payload ({fp_name} cancel book): {payload}")
                url = DME_LEVEL_API_URL + "/booking/cancelconsignment"
                response = requests.delete(url, params={}, json=payload)
                response0 = response.content.decode("utf8").replace("'", '"')
                data0 = json.loads(response0)
                s0 = json.dumps(
                    data0, indent=2, sort_keys=True, default=str
                )  # Just for visual
                # print(f"### Response ({fp_name} cancel book): {s0}")

                try:
                    if response.status_code == 200:
                        booking.b_status = "Closed"
                        booking.b_dateBookedDate = None
                        booking.b_booking_Notes = (
                            "This booking has been closed vis Startrack API"
                        )
                        # booking.v_FPBookingNumber = None
                        booking.save()

                        request_type = f"{fp_name.upper()} CANCEL BOOK"
                        request_status = "SUCCESS"
                        log = Log(
                            request_payload=payload,
                            request_status=request_status,
                            request_type=request_type,
                            response=response0,
                            fk_booking_id=booking.id,
                        ).save()

                        return JsonResponse(
                            {"message": "Successfully cancelled book"}, status=200
                        )
                    else:
                        error_msg = data0
                        _set_error(booking, error_msg)
                        return JsonResponse(
                            {"message": "Failed to cancel book"}, status=400
                        )
                except KeyError:
                    try:
                        request_type = f"{fp_name.upper()} CANCEL BOOK"
                        request_status = "ERROR"
                        oneLog = Log(
                            request_payload=payload,
                            request_status=request_status,
                            request_type=request_type,
                            response=response0,
                            fk_booking_id=booking.id,
                        )
                        oneLog.save()

                        error_msg = data0["errors"]
                        _set_error(booking, error_msg)
                        return JsonResponse({"message": error_msg}, status=400)
                    except KeyError:
                        error_msg = data0
                        _set_error(booking, error_msg)
                        return JsonResponse({"message": s0}, status=400)

            else:
                error_msg = "Booking is not booked yet"
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg}, status=400)
        else:
            return JsonResponse({"message": "Booking is already cancelled"}, status=400)
    except IndexError:
        return JsonResponse({"message": "Booking not found"}, status=400)
    except SyntaxError:
        return JsonResponse({"message": "Booking id is required"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_label(request, fp_name):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["bookingId"]
        booking = Bookings.objects.get(id=booking_id)

        payload = get_create_label_payload(booking, fp_name)

        # print(
        #    f"### Payload ({fp_name} create_label): ",
        #    json.dumps(payload, indent=2, sort_keys=True, default=str),
        # )
        url = DME_LEVEL_API_URL + "/labelling/createlabel"
        response0 = requests.post(url, params={}, json=payload)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True, default=str)  # Just for visual
        # print(f"### Response ({fp_name} create_label): {s0}")

        try:
            time.sleep(15)  # Delay to wait label is created
            payload["consignmentNumber"] = data0[0]["request_id"]
            payload["labelType"] = "PRINT"

            # print(f"### Payload ({fp_name} get_label): {payload}")
            url = DME_LEVEL_API_URL + "/labelling/getlabel"
            response0 = requests.post(url, params={}, json=payload)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print(f"### Response ({fp_name} get_label): {s0}")

            booking.z_label_url = data0["labels"][0]["url"]
            booking.save()

            request_type = f"{fp_name.upper()} GET LABEL"
            request_status = "SUCCESS"
            oneLog = Log(
                request_payload=payload,
                request_status=request_status,
                request_type=request_type,
                response=response0,
                fk_booking_id=booking.id,
            ).save()

            return JsonResponse(
                {"message": f"Successfully created label({booking.z_label_url})"},
                status=200,
            )
        except KeyError:
            try:
                request_type = f"{fp_name.upper()} GET LABEL"
                request_status = "ERROR"
                oneLog = Log(
                    request_payload=payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                ).save()

                error_msg = data0["errors"]
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg}, status=400)
            except TypeError:
                return JsonResponse({"message": s0}, status=400)
            except KeyError:
                return JsonResponse({"message": s0}, status=400)

    except IndexError:
        return JsonResponse({"message": "Booking not found"}, status=400)


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

        # print("Payload(Create Order for ST): ", data)
        url = DME_LEVEL_API_URL + "/order/create"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True, default=str)  # Just for visual
        # print("Response(Create Order for ST): ", s0)

        try:
            request_type = f"{fp_name} CREATE ORDER"
            request_status = "SUCCESS"
            oneLog = Log(
                request_payload=payload,
                request_status=request_status,
                request_type=request_type,
                response=response0,
                fk_booking_id=booking.id,
            ).save()

            for booking in bookings:
                booking.vx_fp_order_id = data0["order_id"]
                booking.save()
            return JsonResponse(
                {"message": f"Successfully create order({booking.vx_fp_order_id})"}
            )
        except KeyError:
            try:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = f"{fp_name.upper()} CREATE ORDER"
                request_status = "ERROR"
                oneLog = Log(
                    request_payload=payload,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                )
                oneLog.save()

                error_msg = data0["errors"]
                _set_error(booking, error_msg)
                return JsonResponse({"message": error_msg})
            except KeyError:
                error_msg = data0
                _set_error(booking, error_msg)
                return JsonResponse({"message": s0})
    except IndexError:
        return JsonResponse({"message": "Booking not found"})


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

            # print(f"### Payload ({fp_name} Get Order Summary): {payload}")
            url = DME_LEVEL_API_URL + "/order/summary"
            response0 = requests.post(url, json=payload, headers=headers)
            response0 = response0.content
            data0 = json.loads(response0)
            # s0 = json.dumps(
            #     data0, indent=2, sort_keys=True, default=str
            # )  # Just for visual
            # print(f"### Response ({fp_name} Get Order Summary): {bytes(data0["pdfData"]["data"])}")

            try:
                file_name = (
                    "biopak_manifest_"
                    + str(booking.vx_fp_order_id)
                    + "_"
                    + str(datetime.now())
                    + ".pdf"
                )

                if IS_PRODUCTION:
                    file_url = f"/opt/s3_public/pdfs/{fp_name.lower()}_au/{file_name}"
                else:
                    file_url = f"/Users/admin/work/goldmine/dme_api/static/pdfs/{fp_name.loer()}_au/{file_name}"

                with open(file_url, "wb") as f:
                    f.write(bytes(data0["pdfData"]["data"]))
                    f.close()

                bookings = Bookings.objects.filter(
                    vx_fp_order_id=booking.vx_fp_order_id
                )

                manifest_timestamp = datetime.now()
                for booking in bookings:
                    booking.z_manifest_url = f"{fp_name.lower()}_au/{file_name}"
                    booking.manifest_timestamp = manifest_timestamp
                    booking.save()

                return JsonResponse({"Success": "Manifest is created successfully."})
            except KeyError:
                error_msg = data0
                _set_error(booking, error_msg)
                return JsonResponse({"message": s0})
        except IndexError:
            error_msg = "Order is not created for this booking."
            _set_error(booking, error_msg)
            return JsonResponse({"message": error_msg})
    except SyntaxError:
        return JsonResponse({"message": "Booking id is required"})
