from django.shortcuts import render
from rest_framework import views, serializers, status
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.http import JsonResponse
from django.http import QueryDict
from django.db.models import Q
from urllib.request import urlopen
import urllib, requests
import json
import datetime
from ast import literal_eval

from .serializers_api import BOK_0_BookingKeysSerializer, BOK_1_headersSerializer, BOK_2_linesSerializer
from .models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines, Bookings
from .models import Log

@api_view(['GET', 'POST'])
def bok_0_bookingkeys(request):
    if request.method == 'GET':
        bok_0_bookingkeys = BOK_0_BookingKeys.objects.all()
        serializer = BOK_0_BookingKeysSerializer(bok_0_bookingkeys, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BOK_0_BookingKeysSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def bok_1_headers(request):
    if request.method == 'GET':
        bok_1_headers = BOK_1_headers.objects.all()
        serializer = BOK_1_headersSerializer(bok_1_headers, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BOK_1_headersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def bok_2_lines(request):
    if request.method == 'GET':
        bok_2_lines = BOK_2_lines.objects.all()
        serializer = BOK_2_linesSerializer(bok_2_lines, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BOK_2_linesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def bok_1_to_bookings(request):
    bok_1_list = BOK_1_headers.objects.filter(success=2)
    mapped_bookings = []

    for bok_1 in bok_1_list:
        new_booking = Bookings(kf_client_id=bok_1.fk_client_id, pk_booking_id=bok_1.pk_header_id, b_clientReference_RA_Numbers=bok_1.b_000_1_b_clientReference_RA_Numbers, DME_price_from_client=bok_1.b_000_2_b_price, total_lines_qty_override=bok_1.b_000_b_total_lines, vx_freight_provider=bok_1.b_001_b_freight_provider, v_vehicle_Type=bok_1.b_002_b_vehicle_type, vx_serviceName=bok_1.b_003_b_service_name, booking_Created_For=bok_1.b_005_b_created_for, booking_Created_For_Email=bok_1.b_006_b_created_for_email, x_ReadyStatus=bok_1.b_007_b_ready_status, b_booking_Category=bok_1.b_008_b_category, b_booking_Priority=bok_1.b_009_b_priority, b_booking_Notes=bok_1.b_010_b_notes, b_handling_Instructions=bok_1.b_014_b_pu_handling_instructions, pu_PickUp_Instructions_Contact=bok_1.b_015_b_pu_instructions_contact, pu_pickup_instructions_address=bok_1.b_016_b_pu_instructions_address, pu_WareHouse_Number=bok_1.b_017_b_pu_warehouse_num, pu_WareHouse_Bay=bok_1.b_018_b_pu_warehouse_bay, b_booking_tail_lift_pickup=bok_1.b_019_b_pu_tail_lift, b_booking_no_operator_pickup=bok_1.b_020_b_pu_num_operators, puPickUpAvailFrom_Date=bok_1.b_021_pu_avail_from_date, pu_PickUp_Avail_Time_Hours=bok_1.b_022_b_pu_avail_from_time_hour, pu_PickUp_Avail_Time_Minutes=bok_1.b_023_b_pu_avail_from_time_minute, pu_PickUp_By_Date_DME=bok_1.b_024_b_pu_by_date, pu_PickUp_By_Time_Hours_DME=bok_1.b_025_b_pu_by_time_hour, pu_PickUp_By_Time_Minutes_DME=bok_1.b_026_b_pu_by_time_minute, pu_Address_Type=bok_1.b_027_b_pu_address_type, puCompany=bok_1.b_028_b_pu_company, pu_Address_Street_1=bok_1.b_029_b_pu_address_street_1, pu_Address_street_2=bok_1.b_030_b_pu_address_street_2, pu_Address_State=bok_1.b_031_b_pu_address_state, pu_Address_Suburb=bok_1.b_032_b_pu_address_suburb, pu_Address_PostalCode=bok_1.b_033_b_pu_address_postalcode, pu_Address_Country=bok_1.b_034_b_pu_address_country, pu_Contact_F_L_Name=bok_1.b_035_b_pu_contact_full_name, pu_email_Group=bok_1.b_036_b_pu_email_group, pu_Email=bok_1.b_037_b_pu_email, pu_Phone_Main=bok_1.b_038_b_pu_phone_main, pu_Phone_Mobile=bok_1.b_039_b_pu_phone_mobile, pu_Comm_Booking_Communicate_Via=bok_1.b_040_b_pu_communicate_via, de_to_addressed_Saved=bok_1.pu_addressed_saved, b_booking_tail_lift_deliver=bok_1.b_041_b_del_tail_lift, b_bookingNoOperatorDeliver=bok_1.b_042_b_del_num_operators, de_to_Pick_Up_Instructions_Contact=bok_1.b_043_b_del_instructions_contact, de_to_PickUp_Instructions_Address=bok_1.b_044_b_del_instructions_address, de_to_WareHouse_Bay=bok_1.b_045_b_del_warehouse_bay, de_to_WareHouse_Number=bok_1.b_046_b_del_warehouse_number, de_Deliver_From_Date=bok_1.b_047_b_del_avail_from_date, de_Deliver_From_Hours=bok_1.b_048_b_del_avail_from_time_hour, de_Deliver_From_Minutes=bok_1.b_049_b_del_avail_from_time_minute, de_Deliver_By_Date=bok_1.b_050_b_del_by_date, de_Deliver_By_Hours=bok_1.b_051_b_del_by_time_hour, de_Deliver_By_Minutes=bok_1.b_052_b_del_by_time_minute, de_To_AddressType=bok_1.b_053_b_del_address_type, deToCompanyName=bok_1.b_054_b_del_company, de_To_Address_Street_1=bok_1.b_055_b_del_address_street_1, de_To_Address_Street_2=bok_1.b_056_b_del_address_street_2, de_To_Address_State=bok_1.b_057_b_del_address_state, de_To_Address_Suburb=bok_1.b_058_b_del_address_suburb, deToAddressPostalCode=bok_1.b_059_b_del_address_postalcode, de_To_Address_Country=bok_1.b_060_b_del_address_country, de_to_Contact_F_LName=bok_1.b_061_b_del_contact_full_name, de_Email_Group_Emails=bok_1.b_062_b_del_email_group, de_Email=bok_1.b_063_b_del_email, de_to_Phone_Main=bok_1.b_064_b_del_phone_main, de_to_Phone_Mobile=bok_1.b_065_b_del_phone_mobile, de_To_Comm_Delivery_Communicate_Via=bok_1.b_066_b_del_communicate_via, total_1_KG_weight_override=bok_1.total_kg, zb_002_client_booking_key=bok_1.v_client_pk_consigment_num, z_CreatedTimestamp=bok_1.z_createdTimeStamp, v_service_Type=bok_1.vx_serviceType_XXX, b_bookingID_Visual=bok_1.b_000_1_b_clientReference_RA_Numbers, fk_client_warehouse=bok_1.fk_client_warehouse)
        new_booking.save()
        bok_1.success = 1
        bok_1.save()
        mapped_bookings.append({'id': new_booking.id, 'b_bookingID_Visual': new_booking.b_bookingID_Visual, 'b_dateBookedDate': new_booking.b_dateBookedDate, 'puPickUpAvailFrom_Date': new_booking.puPickUpAvailFrom_Date, 'b_clientReference_RA_Numbers': new_booking.b_clientReference_RA_Numbers, 'b_status': new_booking.b_status, 'b_status_API': new_booking.b_status_API, 'vx_freight_provider': new_booking.vx_freight_provider, 'vx_serviceName': new_booking.vx_serviceName, 's_05_LatestPickUpDateTimeFinal': new_booking.s_05_LatestPickUpDateTimeFinal, 's_06_LatestDeliveryDateTimeFinal': new_booking.s_06_LatestDeliveryDateTimeFinal, 'v_FPBookingNumber': new_booking.v_FPBookingNumber, 'puCompany': new_booking.puCompany, 'deToCompanyName': new_booking.deToCompanyName});

    return JsonResponse({'mapped_cnt': len(bok_1_list), 'mapped_bookings': mapped_bookings})

@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def st_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="STARTRACK", z_api_issue_update_flag_500=1)   # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
        request_timestamp = datetime.datetime.now()

        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        print(s0)

        try:
            request_id = data0['requestId']
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
            oneLog.save()
            booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)

@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def allied_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="ALLIED", z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        print("==============")
        print(booking.v_FPBookingNumber)
        print(booking.deToAddressPostalCode)
        print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.deToAddressPostalCode}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        print(s0)

        try:
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
            oneLog.save()
            booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def all_trigger(request):
    booking_list = Bookings.objects.filter(z_api_issue_update_flag_500=1)
    results = []

    for booking in booking_list:
        if booking.vx_freight_provider == "ALLIED":
            url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
            data = literal_eval(request.body.decode('utf8'))
            print("==============")
            print(booking.v_FPBookingNumber)
            print(booking.deToAddressPostalCode)
            print("==============")
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                           "destinationPostcode": booking.deToAddressPostalCode}]
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
            print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
                request_type = "TRACKING"
                request_status = "SUCCESS"

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
                oneLog.save()
                booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                booking.save()

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})
        elif booking.vx_freight_provider == "STARTRACK":
            url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
            data = literal_eval(request.body.decode('utf8'))
            print("==============")
            print(booking.v_FPBookingNumber)
            print("==============")
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
            print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
                request_type = "TRACKING"
                request_status = "SUCCESS"

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()
                booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                booking.save()

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def trigger_allied(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="ALLIED",
                                           z_api_issue_update_flag_500=1, b_client_name="seaway")
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        print("==============")
        print(booking.v_FPBookingNumber)
        print(booking.deToAddressPostalCode)
        print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.deToAddressPostalCode}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        print(s0)

        try:
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
            oneLog.save()
            booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def trigger_st(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="STARTRACK",
                                           z_api_issue_update_flag_500=1, b_client_name="BioPak")
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        print("==============")
        print(booking.v_FPBookingNumber)
        print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        print(s0)

        try:
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
            oneLog.save()
            booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
# @authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def hunter_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="HUNTER", z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        print("==============")
        print(booking.v_FPBookingNumber)
        print(booking.deToAddressPostalCode)
        print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.deToAddressPostalCode}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        print(s0)

        try:
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            request_type = "TRACKING"
            request_status = "SUCCESS"
            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=booking.id)
            oneLog.save()
            booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)
