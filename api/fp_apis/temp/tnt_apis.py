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

from api.serializers_api import *
from api.models import *
from django.conf import settings

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

TNT_ACCOUTN_CODES = {
    "live": "30021385",  # Original
}

TNT_KEY_CHAINS = {
    "live": {
        "accountKey": "30021385",
        "accountPassword": "Deliver123"
    },
}


def _set_error(booking, error_msg):
    booking.b_error_Capture = str(error_msg)[:999]
    booking.save()


def _get_account_details(booking):
    if settings.ENV in ["local", "dev"]:
        account_detail = {
            "accountCode": ST_ACCOUTN_CODES["live"],
            **ST_KEY_CHAINS["live"],
        }
    else:
        account_detail = {
            "accountCode": ST_ACCOUTN_CODES[
                booking.fk_client_warehouse.client_warehouse_code
            ],
            **ST_KEY_CHAINS["live"],
        }

    return account_detail


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def tracking(request):
    booking_list = Bookings.objects.filter(
        vx_freight_provider__iexact="tnt", z_api_issue_update_flag_500=1
    )
    results = []

    for booking in booking_list:
        url = DME_LEVEL_API_URL + "/tracking/trackconsignment"
        data = literal_eval(request.body.decode("utf8"))
        data["consignmentDetails"] = [{"consignmentNumber": booking.v_FPBookingNumber}]
        request_timestamp = datetime.now()

        # print('### Payload (ST tracking): ', data)
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True)  # Just for visual
        # print('### Response: ', s0)

        try:
            request_id = data0["requestId"]
            request_payload = {
                "apiUrl": "",
                "accountCode": "",
                "authKey": "",
                "trackingId": "",
            }
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0][
                "consignmentNumber"
            ]
            request_type = "TNT TRACKING"
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

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def book(request):
    results = []
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

            data = {}
            data["spAccountDetails"] = _get_account_details(booking)
            data["serviceProvider"] = "TNT"
            data["readyDate"] = (
                ""
                if booking.puPickUpAvailFrom_Date is None
                else str(booking.puPickUpAvailFrom_Date)
            )
            data["referenceNumber"] = (
                ""
                if booking.b_clientReference_RA_Numbers is None
                else booking.b_clientReference_RA_Numbers
            )
            data["serviceType"] = "R" if booking.vx_serviceName is None else "R"
            data["bookedBy"] = "Mr.CharlieBrown"
            data["pickupAddress"] = {
                "companyName": "" if booking.puCompany is None else booking.puCompany,
                "contact": "Rosie Stokeld"
                if booking.pu_Contact_F_L_Name is None
                else booking.pu_Contact_F_L_Name,
                "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                "instruction": ""
                if booking.pu_PickUp_Instructions_Contact is None
                else booking.pu_PickUp_Instructions_Contact,
                "phoneNumber": "0267651109"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["pickupAddress"]["postalAddress"] = {
                "address1": ""
                if booking.pu_Address_Street_1 is None
                else booking.pu_Address_Street_1,
                "address2": ""
                if booking.pu_Address_street_2 is None
                else booking.pu_Address_street_2,
                "country": ""
                if booking.pu_Address_Country is None
                else booking.pu_Address_Country,
                "postCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
                "state": ""
                if booking.pu_Address_State is None
                else booking.pu_Address_State,
                "suburb": ""
                if booking.pu_Address_Suburb is None
                else booking.pu_Address_Suburb,
                "sortCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
            }
            data["dropAddress"] = {
                "companyName": ""
                if booking.deToCompanyName is None
                else booking.deToCompanyName,
                "contact": "James Sam"
                if booking.de_to_Contact_F_LName is None
                else booking.de_to_Contact_F_LName,
                "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                "instruction": ""
                if booking.de_to_Pick_Up_Instructions_Contact is None
                else booking.de_to_Pick_Up_Instructions_Contact,
                "phoneNumber": "0393920020"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["dropAddress"]["postalAddress"] = {
                "address1": ""
                if booking.de_To_Address_Street_1 is None
                else booking.de_To_Address_Street_1,
                "address2": ""
                if booking.de_To_Address_Street_2 is None
                else booking.de_To_Address_Street_2,
                "country": ""
                if booking.de_To_Address_Country is None
                else booking.de_To_Address_Country,
                "postCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
                "state": ""
                if booking.de_To_Address_State is None
                else booking.de_To_Address_State,
                "suburb": ""
                if booking.de_To_Address_Suburb is None
                else booking.de_To_Address_Suburb,
                "sortCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
            }

            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            items = []
            for line in booking_lines:
                for i in range(line.e_qty):
                    temp_item = {
                        "dangerous": 0,
                        "itemId": "EXP",
                        "packagingType": "CTN",
                        "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                        "length": 0 if line.e_dimLength is None else line.e_dimLength,
                        "quantity": 0 if line.e_qty is None else line.e_qty,
                        "volume": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "weight": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "width": 0 if line.e_dimWidth is None else line.e_dimWidth,
                    }
                    items.append(temp_item)

            data["items"] = items

            # print("### Payload (ST book): ", data)
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print("### Response (ST book): ", s0)

            try:
                request_payload = {
                    "apiUrl": "",
                    "accountCode": "",
                    "authKey": "",
                    "trackingId": "",
                }
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0["consignmentNumber"]
                request_type = "TNT BOOK"
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
                        request_payload=data,
                        request_status="ERROR",
                        request_type="TNT BOOK",
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
def pricing(request):
    results = []
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

            data = {}
            data["spAccountDetails"] = _get_account_details(booking)
            data["serviceProvider"] = "TNT"
            data["readyDate"] = (
                ""
                if booking.puPickUpAvailFrom_Date is None
                else str(booking.puPickUpAvailFrom_Date)
            )
            data["referenceNumber"] = (
                ""
                if booking.b_clientReference_RA_Numbers is None
                else booking.b_clientReference_RA_Numbers
            )
            data["serviceType"] = "R" if booking.vx_serviceName is None else "R"
            data["bookedBy"] = "Mr.CharlieBrown"
            data["pickupAddress"] = {
                "companyName": "" if booking.puCompany is None else booking.puCompany,
                "contact": "Rosie Stokeld"
                if booking.pu_Contact_F_L_Name is None
                else booking.pu_Contact_F_L_Name,
                "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                "instruction": ""
                if booking.pu_PickUp_Instructions_Contact is None
                else booking.pu_PickUp_Instructions_Contact,
                "phoneNumber": "0267651109"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["pickupAddress"]["postalAddress"] = {
                "address1": ""
                if booking.pu_Address_Street_1 is None
                else booking.pu_Address_Street_1,
                "address2": ""
                if booking.pu_Address_street_2 is None
                else booking.pu_Address_street_2,
                "country": ""
                if booking.pu_Address_Country is None
                else booking.pu_Address_Country,
                "postCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
                "state": ""
                if booking.pu_Address_State is None
                else booking.pu_Address_State,
                "suburb": ""
                if booking.pu_Address_Suburb is None
                else booking.pu_Address_Suburb,
                "sortCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
            }
            data["dropAddress"] = {
                "companyName": ""
                if booking.deToCompanyName is None
                else booking.deToCompanyName,
                "contact": "James Sam"
                if booking.de_to_Contact_F_LName is None
                else booking.de_to_Contact_F_LName,
                "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                "instruction": ""
                if booking.de_to_Pick_Up_Instructions_Contact is None
                else booking.de_to_Pick_Up_Instructions_Contact,
                "phoneNumber": "0393920020"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["dropAddress"]["postalAddress"] = {
                "address1": ""
                if booking.de_To_Address_Street_1 is None
                else booking.de_To_Address_Street_1,
                "address2": ""
                if booking.de_To_Address_Street_2 is None
                else booking.de_To_Address_Street_2,
                "country": ""
                if booking.de_To_Address_Country is None
                else booking.de_To_Address_Country,
                "postCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
                "state": ""
                if booking.de_To_Address_State is None
                else booking.de_To_Address_State,
                "suburb": ""
                if booking.de_To_Address_Suburb is None
                else booking.de_To_Address_Suburb,
                "sortCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
            }

            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            items = []
            for line in booking_lines:
                for i in range(line.e_qty):
                    temp_item = {
                        "dangerous": 0,
                        "itemId": "EXP",
                        "packagingType": "CTN",
                        "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                        "length": 0 if line.e_dimLength is None else line.e_dimLength,
                        "quantity": 0 if line.e_qty is None else line.e_qty,
                        "volume": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "weight": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "width": 0 if line.e_dimWidth is None else line.e_dimWidth,
                    }
                    items.append(temp_item)

            data["items"] = items

            # print("### Payload (ST book): ", data)
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print("### Response (ST book): ", s0)

            try:
                request_payload = {
                    "apiUrl": "",
                    "accountCode": "",
                    "authKey": "",
                    "trackingId": "",
                }
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0["consignmentNumber"]
                request_type = "TNT BOOK"
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
                        request_payload=data,
                        request_status="ERROR",
                        request_type="TNT BOOK",
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
def pod(request):
    results = []
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

            data = {}
            data["spAccountDetails"] = _get_account_details(booking)
            data["serviceProvider"] = "TNT"
            data["readyDate"] = (
                ""
                if booking.puPickUpAvailFrom_Date is None
                else str(booking.puPickUpAvailFrom_Date)
            )
            data["referenceNumber"] = (
                ""
                if booking.b_clientReference_RA_Numbers is None
                else booking.b_clientReference_RA_Numbers
            )
            data["serviceType"] = "R" if booking.vx_serviceName is None else "R"
            data["bookedBy"] = "Mr.CharlieBrown"
            data["pickupAddress"] = {
                "companyName": "" if booking.puCompany is None else booking.puCompany,
                "contact": "Rosie Stokeld"
                if booking.pu_Contact_F_L_Name is None
                else booking.pu_Contact_F_L_Name,
                "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                "instruction": ""
                if booking.pu_PickUp_Instructions_Contact is None
                else booking.pu_PickUp_Instructions_Contact,
                "phoneNumber": "0267651109"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["pickupAddress"]["postalAddress"] = {
                "address1": ""
                if booking.pu_Address_Street_1 is None
                else booking.pu_Address_Street_1,
                "address2": ""
                if booking.pu_Address_street_2 is None
                else booking.pu_Address_street_2,
                "country": ""
                if booking.pu_Address_Country is None
                else booking.pu_Address_Country,
                "postCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
                "state": ""
                if booking.pu_Address_State is None
                else booking.pu_Address_State,
                "suburb": ""
                if booking.pu_Address_Suburb is None
                else booking.pu_Address_Suburb,
                "sortCode": ""
                if booking.pu_Address_PostalCode is None
                else booking.pu_Address_PostalCode,
            }
            data["dropAddress"] = {
                "companyName": ""
                if booking.deToCompanyName is None
                else booking.deToCompanyName,
                "contact": "James Sam"
                if booking.de_to_Contact_F_LName is None
                else booking.de_to_Contact_F_LName,
                "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                "instruction": ""
                if booking.de_to_Pick_Up_Instructions_Contact is None
                else booking.de_to_Pick_Up_Instructions_Contact,
                "phoneNumber": "0393920020"
                if booking.pu_Phone_Main is None
                else booking.pu_Phone_Main,
            }
            data["dropAddress"]["postalAddress"] = {
                "address1": ""
                if booking.de_To_Address_Street_1 is None
                else booking.de_To_Address_Street_1,
                "address2": ""
                if booking.de_To_Address_Street_2 is None
                else booking.de_To_Address_Street_2,
                "country": ""
                if booking.de_To_Address_Country is None
                else booking.de_To_Address_Country,
                "postCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
                "state": ""
                if booking.de_To_Address_State is None
                else booking.de_To_Address_State,
                "suburb": ""
                if booking.de_To_Address_Suburb is None
                else booking.de_To_Address_Suburb,
                "sortCode": ""
                if booking.de_To_Address_PostalCode is None
                else booking.de_To_Address_PostalCode,
            }

            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=booking.pk_booking_id
            )

            items = []
            for line in booking_lines:
                for i in range(line.e_qty):
                    temp_item = {
                        "dangerous": 0,
                        "itemId": "EXP",
                        "packagingType": "CTN",
                        "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                        "length": 0 if line.e_dimLength is None else line.e_dimLength,
                        "quantity": 0 if line.e_qty is None else line.e_qty,
                        "volume": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "weight": 0
                        if line.e_weightPerEach is None
                        else line.e_weightPerEach,
                        "width": 0 if line.e_dimWidth is None else line.e_dimWidth,
                    }
                    items.append(temp_item)

            data["items"] = items

            # print("### Payload (ST book): ", data)
            url = DME_LEVEL_API_URL + "/pod/fetchpod"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print("### Response (ST book): ", s0)

            try:
                request_payload = {
                    "apiUrl": "",
                    "accountCode": "",
                    "authKey": "",
                    "trackingId": "",
                }
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0["consignmentNumber"]
                request_type = "TNT POD"
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
                        request_payload=data,
                        request_status="ERROR",
                        request_type="TNT POD",
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

