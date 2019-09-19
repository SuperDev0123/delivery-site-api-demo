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
    production = False  # Local
else:
    production = True  # Dev

if production:
    DME_LEVEL_API_URL = "http://52.62.109.115:3000"
else:
    DME_LEVEL_API_URL = "http://localhost:3000"

DME_LEVEL_API_URL = "http://localhost:3000"


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def tracking(request):
    booking_list = Bookings.objects.filter(
        vx_freight_provider__iexact="startrack", z_api_issue_update_flag_500=1
    )
    results = []
    # print("booking_list: ", booking_list)
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
            request_type = "TRACKING"
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
            booking = Bookings.objects.filter(id=booking_id)[0]

            if booking.b_status.lower() != "ready for booking":
                return JsonResponse(
                    {"message": "Booking is already booked."}, status=400
                )

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return JsonResponse(
                    {"message": "State for pickup postal address is required."},
                    status=400,
                )

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return JsonResponse(
                    {"message": "Suburb name for pickup postal address is required."},
                    status=400,
                )

            data = {}
            data["spAccountDetails"] = {
                "accountCode": "00956684",
                "accountState": "NSW",
                "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                "accountPassword": "xab801a41e663b5cb889",
            }
            data["serviceProvider"] = "ST"
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
                        "packagingType": "PAL",
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

            print("### Payload (ST book): ", data)
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            print("### Response (ST book): ", s0)

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
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0["consignmentNumber"]
                # booking.fk_fp_pickup_id = data0["requestId"]
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
                    {"message": f"Successfully booked({data0['consignmentNumber']})"}
                )
            except KeyError:
                try:
                    log = Log(
                        request_payload=data,
                        request_status="ERROR",
                        request_type="ST BOOKING",
                        response=response0,
                        fk_booking_id=booking.id,
                    ).save()

                    booking.b_error_Capture = data0["errorMsg"]
                    booking.save()
                    return JsonResponse(
                        {"message": booking.b_error_Capture}, status=400
                    )
                except KeyError:
                    booking.b_error_Capture = "ST Booking failed"
                    booking.save()
                    return JsonResponse({"message": s0}, status=400)

        except IndexError:
            return JsonResponse({"message": "Booking not found"}, status=400)

        except TypeError:
            return JsonResponse({"message": "eqty is none"}, status=400)

    except SyntaxError:
        return JsonResponse({"message": "booking id is required"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def edit_book(request):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]

        try:
            booking = Bookings.objects.get(id=booking_id)

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return JsonResponse(
                    {"Error": "State for pickup postal address is required."}
                )

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return booking_id(
                    {"Error": "suburb name for pickup postal address is required."}
                )

            data = {}
            data["spAccountDetails"] = {
                "accountCode": "00956684",
                "accountState": "NSW",
                "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                "accountPassword": "xab801a41e663b5cb889",
            }
            data["serviceProvider"] = "ST"
            data["consignmentNumber"] = booking.v_FPBookingNumber
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
                temp_item = {
                    "dangerous": 0,
                    "itemId": "EXP",
                    "packagingType": "PAL",
                    "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                    "length": 0 if line.e_dimLength is None else line.e_dimLength,
                    "quantity": 0 if line.e_qty is None else line.e_qty,
                    "volume": 0
                    if line.e_1_Total_dimCubicMeter is None
                    else line.e_1_Total_dimCubicMeter,
                    "weight": 0
                    if line.e_Total_KG_weight is None
                    else line.e_Total_KG_weight,
                    "width": 0 if line.e_dimWidth is None else line.e_dimWidth,
                }
                items.append(temp_item)
            data["items"] = items

            # print(data)
            url = DME_LEVEL_API_URL + "/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            # print(s0)

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
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0["consignmentNumber"]
                # booking.fk_fp_pickup_id = data0["requestId"]
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
                    )
                    book_con.save()

                return JsonResponse(
                    {"message": f"Successfully edit book({data0['consignmentNumber']})"}
                )
            except KeyError:
                try:
                    request_type = "EDIT ST BOOKING"
                    request_status = "ERROR"
                    oneLog = Log(
                        request_payload=data,
                        request_status=request_status,
                        request_type=request_type,
                        response=response0,
                        fk_booking_id=booking.id,
                    )
                    oneLog.save()

                    booking.b_error_Capture = data0["errorMsg"]
                    booking.save()
                    return JsonResponse({"Error": data0["errorMsg"]}, status=400)
                except KeyError:
                    booking.b_error_Capture = "Failed to edit book"
                    booking.save()
                    return JsonResponse({"Error": s0}, status=400)

        except IndexError:
            return JsonResponse({"message": "Booking not found"}, status=400)

    except SyntaxError:
        return JsonResponse({"message": "Booking id is required"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def cancel_book(request):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["booking_id"]
        booking = Bookings.objects.get(id=booking_id)

        if booking.b_status != "Closed":
            if booking.b_dateBookedDate is not None:
                data = {}
                data["spAccountDetails"] = {
                    "accountCode": "00956684",
                    "accountState": "NSW",
                    "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                    "accountPassword": "xab801a41e663b5cb889",
                }
                data["serviceProvider"] = "ST"
                data["consignmentNumbers"] = [booking.v_FPBookingNumber]

                print("### Payload (ST cancel book): ", data)
                url = DME_LEVEL_API_URL + "/booking/cancelconsignment"
                response = requests.delete(url, params={}, json=data)
                response0 = response.content.decode("utf8").replace("'", '"')
                data0 = json.loads(response0)
                s0 = json.dumps(
                    data0, indent=2, sort_keys=True, default=str
                )  # Just for visual
                print("### Response (ST cancel book): ", s0)

                try:
                    if response.status_code == 200:
                        booking.b_status = "Closed"
                        booking.b_booking_Notes = (
                            "This booking has been closed vis Startrack API"
                        )
                        booking.v_FPBookingNumber = None
                        booking.save()

                        request_type = "CANCEL ST BOOKING"
                        request_status = "SUCCESS"
                        log = Log(
                            request_payload=data,
                            request_status=request_status,
                            request_type=request_type,
                            response=response0,
                            fk_booking_id=booking.id,
                        ).save()

                        return JsonResponse(
                            {"message": "Successfully cancelled book"}, status=200
                        )
                    else:
                        return JsonResponse(
                            {"message": "Failed to cancel book"}, status=200
                        )
                except KeyError:
                    request_type = "CANCEL ST BOOKING"
                    request_status = "ERROR"
                    log = Log(
                        request_payload=data,
                        request_status=request_status,
                        request_type=request_type,
                        response=response0,
                        fk_booking_id=booking.id,
                    ).save()

                    return JsonResponse(
                        {"message": "Failed to cancel book"}, status=400
                    )
            else:
                return JsonResponse(
                    {"message": "Booking is not booked yet"}, status=400
                )
        else:
            return JsonResponse({"message": "Booking is closed"}, status=400)

    except IndexError:
        return JsonResponse({"message": "Booking not found"}, status=400)

    except SyntaxError:
        return JsonResponse({"message": "booking id is required"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_label(request):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_id = body["bookingId"]
        booking = Bookings.objects.get(id=booking_id)

        data = {}
        data["spAccountDetails"] = {
            "accountCode": "00956684",
            "accountState": "NSW",
            "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
            "accountPassword": "xab801a41e663b5cb889",
        }
        data["serviceProvider"] = "ST"
        data["consignmentNumber"] = booking.v_FPBookingNumber
        data["type"] = "PRINT"

        confirmation_items = Api_booking_confirmation_lines.objects.filter(
            fk_booking_id=booking.pk_booking_id
        )

        items = []
        for item in confirmation_items:
            temp_item = {"itemId": item.api_item_id, "packagingType": "PAL"}
            items.append(temp_item)
        data["items"] = items

        page_format = [
            {
                "branded": "_CMK0E6mwiMAAAFoYvcg7Ha9",
                "branded": False,
                "layout": "A4-1pp",
                "leftOffset": 0,
                "topOffset": 0,
                "typeOfPost": "Express Post",
            }
        ]
        data["pageFormat"] = page_format

        print(
            "### Payload (ST create_label): ",
            json.dumps(data, indent=2, sort_keys=True, default=str),
        )
        url = DME_LEVEL_API_URL + "/labelling/createlabel"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True, default=str)  # Just for visual
        print("### Response (ST create_label): ", s0)

        try:
            time.sleep(10)  # Delay to wait label is created
            data["consignmentNumber"] = data0[0]["request_id"]
            data["labelType"] = "PRINT"

            print("### Payload (ST get_label): ", data)
            url = DME_LEVEL_API_URL + "/labelling/getlabel"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            print("### Response (ST get_label): ", s0)

            booking.z_label_url = data0["labels"][0]["url"]
            booking.save()

            request_type = "ST Label"
            request_status = "SUCCESS"
            oneLog = Log(
                request_payload=data,
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
                request_type = "ST Label"
                request_status = "ERROR"
                oneLog = Log(
                    request_payload=data,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                ).save()

                return JsonResponse({"message": data0["errorMsg"]}, status=400)
            except TypeError:
                return JsonResponse({"message": s0}, status=400)
            except KeyError:
                return JsonResponse({"message": s0}, status=400)

    except IndexError:
        return JsonResponse({"message": "Booking not found"}, status=400)


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def create_order(request):
    results = []
    body = literal_eval(request.body.decode("utf8"))
    booking_ids = body["bookingIds"]

    try:
        bookings = Bookings.objects.filter(
            pk__in=booking_ids,
            b_status="Booked",
            vx_freight_provider__iexact="startrack",
        )

        data = {}
        data["spAccountDetails"] = {
            "accountCode": "00956684",
            "accountState": "NSW",
            "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
            "accountPassword": "xab801a41e663b5cb889",
        }
        data["serviceProvider"] = "ST"
        data["paymentMethods"] = "CHARGE_TO_ACCOUNT"
        data["referenceNumber"] = "refer1"

        consignmentNumbers = []
        for booking in bookings:
            consignmentNumbers.append(booking.v_FPBookingNumber)
        data["consignmentNumbers"] = consignmentNumbers

        print("Payload(Create Order for ST): ", data)
        url = DME_LEVEL_API_URL + "/order/create"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode("utf8").replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=2, sort_keys=True, default=str)  # Just for visual
        print("Response(Create Order for ST): ", s0)

        try:
            request_type = "Create Order"
            request_status = "SUCCESS"
            oneLog = Log(
                request_payload=data,
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
                request_type = "Create Order"
                request_status = "ERROR"
                oneLog = Log(
                    request_payload=data,
                    request_status=request_status,
                    request_type=request_type,
                    response=response0,
                    fk_booking_id=booking.id,
                )
                oneLog.save()
                return JsonResponse({"Error": data0["errorMsg"]})
            except KeyError:
                return JsonResponse({"Error": s0})
    except IndexError:
        return JsonResponse({"message": "Booking not found"})


@api_view(["POST"])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def order_summary(request):
    try:
        body = literal_eval(request.body.decode("utf8"))
        booking_ids = body["bookingIds"]

        try:
            booking = Bookings.objects.get(id=booking_ids[0])

            data = {}
            data["spAccountDetails"] = {
                "accountCode": "00956684",
                "accountState": "NSW",
                "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                "accountPassword": "xab801a41e663b5cb889",
            }
            data["serviceProvider"] = "ST"
            data["orderId"] = booking.vx_fp_order_id

            print("### Payload (Get Order Summary): ", data)
            url = DME_LEVEL_API_URL + "/order/summary"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode("utf8").replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(
                data0, indent=2, sort_keys=True, default=str
            )  # Just for visual
            print("### Response (Get Order Summary): ", s0)

            try:
                file_name = (
                    "biopak_manifest_"
                    + str(booking.vx_fp_order_id)
                    + "_"
                    + str(datetime.now())
                    + ".pdf"
                )
                file_url = "/var/www/html/dme_api/static/pdfs/" + file_name

                with open(os.path.expanduser(file_url), "wb") as fout:
                    fout.write(base64.decodestring(data0["pdfData"].encode("utf-8")))

                bookings = Bookings.objects.filter(
                    vx_fp_order_id=booking.vx_fp_order_id
                )
                for book in bookings:
                    book.z_manifest_url = file_name
                    book.save()

                return JsonResponse({"Success": "Manifest is created successfully."})
            except KeyError:
                return JsonResponse({"Error": s0})
        except IndexError:
            return JsonResponse({"message": "Order is not created for this booking."})
    except SyntaxError:
        return JsonResponse({"message": "booking id is required"})
