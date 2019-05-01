import base64, os
import codecs
import time

from django.http import HttpResponse
import xlsxwriter as xlsxwriter
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

from .serializers_api import *
from .models import *
from django.conf import settings

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
        bok_1_header = request.data
        b_client_warehouse_code = bok_1_header['b_client_warehouse_code']
        warehouse = Client_warehouses.objects.get(client_warehouse_code=b_client_warehouse_code)
        bok_1_header['fk_client_warehouse'] = warehouse.pk_id_client_warehouses
        serializer = BOK_1_headersSerializer(data=bok_1_header)
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
        new_booking = Bookings(kf_client_id=bok_1.fk_client_id, pk_booking_id=bok_1.pk_header_id,
                               b_clientReference_RA_Numbers=bok_1.b_000_1_b_clientReference_RA_Numbers,
                               DME_price_from_client=bok_1.b_000_2_b_price,
                               total_lines_qty_override=bok_1.b_000_b_total_lines,
                               vx_freight_provider=bok_1.b_001_b_freight_provider,
                               v_vehicle_Type=bok_1.b_002_b_vehicle_type, vx_serviceName=bok_1.b_003_b_service_name,
                               booking_Created_For=bok_1.b_005_b_created_for,
                               booking_Created_For_Email=bok_1.b_006_b_created_for_email,
                               x_ReadyStatus=bok_1.b_007_b_ready_status, b_booking_Category=bok_1.b_008_b_category,
                               b_booking_Priority=bok_1.b_009_b_priority, b_booking_Notes=bok_1.b_010_b_notes,
                               b_handling_Instructions=bok_1.b_014_b_pu_handling_instructions,
                               pu_PickUp_Instructions_Contact=bok_1.b_015_b_pu_instructions_contact,
                               pu_pickup_instructions_address=bok_1.b_016_b_pu_instructions_address,
                               pu_WareHouse_Number=bok_1.b_017_b_pu_warehouse_num,
                               pu_WareHouse_Bay=bok_1.b_018_b_pu_warehouse_bay,
                               b_booking_tail_lift_pickup=bok_1.b_019_b_pu_tail_lift,
                               b_booking_no_operator_pickup=bok_1.b_020_b_pu_num_operators,
                               puPickUpAvailFrom_Date=bok_1.b_021_pu_avail_from_date,
                               pu_PickUp_Avail_Time_Hours=bok_1.b_022_b_pu_avail_from_time_hour,
                               pu_PickUp_Avail_Time_Minutes=bok_1.b_023_b_pu_avail_from_time_minute,
                               pu_PickUp_By_Date_DME=bok_1.b_024_b_pu_by_date,
                               pu_PickUp_By_Time_Hours_DME=bok_1.b_025_b_pu_by_time_hour,
                               pu_PickUp_By_Time_Minutes_DME=bok_1.b_026_b_pu_by_time_minute,
                               pu_Address_Type=bok_1.b_027_b_pu_address_type, puCompany=bok_1.b_028_b_pu_company,
                               pu_Address_Street_1=bok_1.b_029_b_pu_address_street_1,
                               pu_Address_street_2=bok_1.b_030_b_pu_address_street_2,
                               pu_Address_State=bok_1.b_031_b_pu_address_state,
                               pu_Address_Suburb=bok_1.b_032_b_pu_address_suburb,
                               pu_Address_PostalCode=bok_1.b_033_b_pu_address_postalcode,
                               pu_Address_Country=bok_1.b_034_b_pu_address_country,
                               pu_Contact_F_L_Name=bok_1.b_035_b_pu_contact_full_name,
                               pu_email_Group=bok_1.b_036_b_pu_email_group, pu_Email=bok_1.b_037_b_pu_email,
                               pu_Phone_Main=bok_1.b_038_b_pu_phone_main, pu_Phone_Mobile=bok_1.b_039_b_pu_phone_mobile,
                               pu_Comm_Booking_Communicate_Via=bok_1.b_040_b_pu_communicate_via,
                               de_to_addressed_Saved=bok_1.pu_addressed_saved,
                               b_booking_tail_lift_deliver=bok_1.b_041_b_del_tail_lift,
                               b_bookingNoOperatorDeliver=bok_1.b_042_b_del_num_operators,
                               de_to_Pick_Up_Instructions_Contact=bok_1.b_043_b_del_instructions_contact,
                               de_to_PickUp_Instructions_Address=bok_1.b_044_b_del_instructions_address,
                               de_to_WareHouse_Bay=bok_1.b_045_b_del_warehouse_bay,
                               de_to_WareHouse_Number=bok_1.b_046_b_del_warehouse_number,
                               de_Deliver_From_Date=bok_1.b_047_b_del_avail_from_date,
                               de_Deliver_From_Hours=bok_1.b_048_b_del_avail_from_time_hour,
                               de_Deliver_From_Minutes=bok_1.b_049_b_del_avail_from_time_minute,
                               de_Deliver_By_Date=bok_1.b_050_b_del_by_date,
                               de_Deliver_By_Hours=bok_1.b_051_b_del_by_time_hour,
                               de_Deliver_By_Minutes=bok_1.b_052_b_del_by_time_minute,
                               de_To_AddressType=bok_1.b_053_b_del_address_type,
                               deToCompanyName=bok_1.b_054_b_del_company,
                               de_To_Address_Street_1=bok_1.b_055_b_del_address_street_1,
                               de_To_Address_Street_2=bok_1.b_056_b_del_address_street_2,
                               de_To_Address_State=bok_1.b_057_b_del_address_state,
                               de_To_Address_Suburb=bok_1.b_058_b_del_address_suburb,
                               de_To_Address_PostalCode=bok_1.b_059_b_del_address_postalcode,
                               de_To_Address_Country=bok_1.b_060_b_del_address_country,
                               de_to_Contact_F_LName=bok_1.b_061_b_del_contact_full_name,
                               de_Email_Group_Emails=bok_1.b_062_b_del_email_group, de_Email=bok_1.b_063_b_del_email,
                               de_to_Phone_Main=bok_1.b_064_b_del_phone_main,
                               de_to_Phone_Mobile=bok_1.b_065_b_del_phone_mobile,
                               de_To_Comm_Delivery_Communicate_Via=bok_1.b_066_b_del_communicate_via,
                               total_1_KG_weight_override=bok_1.total_kg,
                               zb_002_client_booking_key=bok_1.v_client_pk_consigment_num,
                               z_CreatedTimestamp=bok_1.z_createdTimeStamp, v_service_Type=bok_1.vx_serviceType_XXX,
                               b_bookingID_Visual=bok_1.b_000_1_b_clientReference_RA_Numbers,
                               fk_client_warehouse=bok_1.fk_client_warehouse)
        new_booking.save()
        bok_1.success = 1
        bok_1.save()
        mapped_bookings.append({'id': new_booking.id, 'b_bookingID_Visual': new_booking.b_bookingID_Visual,
                                'b_dateBookedDate': new_booking.b_dateBookedDate,
                                'puPickUpAvailFrom_Date': new_booking.puPickUpAvailFrom_Date,
                                'b_clientReference_RA_Numbers': new_booking.b_clientReference_RA_Numbers,
                                'b_status': new_booking.b_status, 'b_status_API': new_booking.b_status_API,
                                'vx_freight_provider': new_booking.vx_freight_provider,
                                'vx_serviceName': new_booking.vx_serviceName,
                                's_05_LatestPickUpDateTimeFinal': new_booking.s_05_LatestPickUpDateTimeFinal,
                                's_06_LatestDeliveryDateTimeFinal': new_booking.s_06_LatestDeliveryDateTimeFinal,
                                'v_FPBookingNumber': new_booking.v_FPBookingNumber, 'puCompany': new_booking.puCompany,
                                'deToCompanyName': new_booking.deToCompanyName});

    return JsonResponse({'mapped_cnt': len(bok_1_list), 'mapped_bookings': mapped_bookings})


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def st_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="STARTRACK",
                                           z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []
    # print("Response ", booking_list)
    for booking in booking_list:
        # print("booking", booking)
        url = "http://52.62.102.72:8080/dme-api-sit/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
        request_timestamp = datetime.now()

        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        # print(s0)

        try:
            request_id = data0['requestId']
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
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def allied_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="ALLIED",
                                           z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.62.102.72:8080/dme-api-sit/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        # print("==============")
        # print(booking.v_FPBookingNumber)
        # print(booking.de_To_Address_PostalCode)
        # print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.de_To_Address_PostalCode}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        # print(s0)

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
            booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.now()
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
        if booking.vx_freight_provider == "Allied" and booking.b_client_name == "Seaway":
            url = "http://35.161.204.104:8081/dme-api/tracking/trackconsignment"
            data = {}
            # print("==============")
            # print(booking.v_FPBookingNumber)
            # print(booking.de_To_Address_PostalCode)
            # print("==============")
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                           "destinationPostcode": booking.de_To_Address_PostalCode}]
            data['spAccountDetails'] = {"accountCode": "SEATEM", "accountState": "NSW",
                                        "accountKey": "ce0d58fd22ae8619974958e65302a715"}
            data['serviceProvider'] = "ALLIED"

            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
            # print(s0)

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
                try:
                    booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                    booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.now()
                    if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Delivered in Full':
                        booking.s_21_ActualDeliveryTimeStamp = datetime.now()

                    booking.save()
                except IndexError:
                    results.append({"Error": "Index Error"})

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})
        elif booking.vx_freight_provider == "STARTRACK":
            url = "http://35.161.204.104:8081/dme-api/tracking/trackconsignment"
            data = {}
            # print("==============")
            # print(booking.v_FPBookingNumber)
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
            data['spAccountDetails'] = {"accountCode": "10149943", "accountState": "NSW",
                                        "accountPassword": "x81775935aece65541c9",
                                        "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134"}
            data['serviceProvider'] = "ST"

            # print(data)
            # print("==============")
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
            # print(s0)

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
                try:
                    booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                    booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.now()
                    if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Delivered in Full':
                        booking.s_21_ActualDeliveryTimeStamp = datetime.now()
                    booking.save()
                except IndexError:
                    results.append({"Error": "Index Error"})

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def trigger_allied(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="Allied",
                                           z_api_issue_update_flag_500='1', b_status='Booked')
    results = []
    for booking in booking_list:
        url = "http://35.161.204.104:8081/dme-api/tracking/trackconsignment"
        data = {}
        # print("==============")
        # print(booking.v_FPBookingNumber)
        # print(booking.de_To_Address_PostalCode)
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.de_To_Address_PostalCode}]
        data['spAccountDetails'] = {"accountCode": "SEATEM", "accountState": "NSW",
                                    "accountKey": "ce0d58fd22ae8619974958e65302a715"}
        data['serviceProvider'] = "ALLIED"

        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual

        try:
            request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
            request_payload["apiUrl"] = url
            request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
            request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
            request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
            data['url'] = url
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=data, request_status=request_status, request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()
            try:
                new_status = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                if booking.b_status_API != new_status:
                    history = Dme_status_history(fk_booking_id=booking.id, status_old=booking.b_status_API,
                                                 notes=str(booking.b_status_API) + " ---> " + str(new_status),
                                                 status_last=new_status,
                                                 api_status_time_stamp=datetime.now(),
                                                 booking_request_data=request_payload)
                    history.save()
                booking.b_status_API = new_status
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.now()
                if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0][
                    'status'] == 'Shipment has been delivered.':
                    booking.z_api_issue_update_flag_500 = 0
                    booking.s_21_ActualDeliveryTimeStamp = \
                        data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['statusDate']
                    booking.s_21_actual_delivery_timestamp = \
                        data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['statusDate']

                try:
                    pod_file = data0['consignmentTrackDetails'][0]["pods"][0]['podData']

                    warehouse_name = booking.fk_client_warehouse.client_warehouse_code
                    file_name = "POD_" + \
                                str(warehouse_name) + "_" + \
                                booking.b_clientReference_RA_Numbers + "_" + \
                                booking.v_FPBookingNumber + "_" + \
                                str(booking.b_bookingID_Visual) + '.png'
                    file_url = '/var/www/html/dme_api/static/imgs/' + file_name

                    with open(os.path.expanduser(file_url), 'wb') as fout:
                        fout.write(
                            base64.decodestring(pod_file.encode('utf-8')))
                    booking.z_pod_url = file_name
                except IndexError:
                    results.append({"Error": "Index Error"})
                except KeyError:
                    results.append({"Error": "Key Error"})

                try:
                    pod_file = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['signatureImage']
                    warehouse_name = booking.fk_client_warehouse.client_warehouse_code
                    file_name = "pod_signed_" + \
                                str(warehouse_name) + "_" + \
                                booking.b_clientReference_RA_Numbers + "_" + \
                                booking.v_FPBookingNumber + "_" + \
                                str(booking.b_bookingID_Visual) + '.png'
                    file_url = '/var/www/html/dme_api/static/imgs/' + file_name

                    with open(os.path.expanduser(file_url), 'wb') as fout:
                        fout.write(
                            base64.decodestring(pod_file.encode('utf-8')))

                    booking.z_pod_signed_url = file_name
                except IndexError:
                    results.append({"Error": "Index Error"})
                except KeyError:
                    results.append({"Error": "Key Error"})

                booking.vx_fp_pu_eta_time = data0['consignmentTrackDetails'][0]['scheduledPickupDate']
                booking.vx_fp_del_eta_time = data0['consignmentTrackDetails'][0]['scheduledDeliveryDate']

                booking.save()

                # print("yes")
            except IndexError:
                booking.save()
                # print("no")

            # print("==============")
            results.append({"Created Log ID": oneLog.id})
        except KeyError as e:
            results.append({"Error": str(e)})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def trigger_st(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="STARTRACK",
                                           z_api_issue_update_flag_500=1, b_client_name="BioPak")
    results = []

    for booking in booking_list:
        url = "http://35.161.204.104:8081/dme-api/tracking/trackconsignment"
        data = {}
        # print("==============")
        # print(booking.v_FPBookingNumber)
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
        data['spAccountDetails'] = {"accountCode": "10149943", "accountState": "NSW",
                                    "accountPassword": "x81775935aece65541c9",
                                    "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134"}
        data['serviceProvider'] = "ST"

        # print(data)
        # print("==============")
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        # print(s0)

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
            try:
                booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.now()
                if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0][
                    'status'] == 'Delivered in Full':
                    booking.s_21_ActualDeliveryTimeStamp = datetime.now()
                booking.save()
            except IndexError:
                results.append({"Error": "Index Error"})

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
# @authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def hunter_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="HUNTER",
                                           z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.62.102.72:8080/dme-api-sit/tracking/trackconsignment"
        data = literal_eval(request.body.decode('utf8'))
        # print("==============")
        # print(booking.v_FPBookingNumber)
        # print(booking.de_To_Address_PostalCode)
        # print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.de_To_Address_PostalCode}]
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
        # print(s0)

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
            booking.save()

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            request_type = "TRACKING"
            request_status = "ERROR"
            oneLog = Log(request_payload=data, request_status=request_status,
                         request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()

            results.append({"Error": "Too many request"})

    return Response(results)


def get_label_allied_fn(bid):
    results = []
    try:
        booking = Bookings.objects.filter(id=bid)[0]

        data = {}

        data['spAccountDetails'] = {"accountCode": "SEATEM", "accountState": "NSW",
                                    "accountKey": "ce0d58fd22ae8619974958e65302a715"}
        data['serviceProvider'] = "ALLIED"
        data['consignmentNumber'] = booking.v_FPBookingNumber
        data['destinationPostcode'] = booking.de_To_Address_PostalCode

        data['labelType'] = "1"
        # print(data)

        url = "http://35.161.204.104:8081/dme-api/labelling/getlabel"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
        # print(s0)

        try:
            file_url = '/var/www/html/dme_api/static/pdfs/' + str(
                booking.fk_client_warehouse.client_warehouse_code) + "_" + booking.b_clientReference_RA_Numbers + "_" + str(
                booking.b_bookingID_Visual) + '.pdf'

            with open(os.path.expanduser(file_url), 'wb') as fout:
                fout.write(base64.decodestring(data0["encodedPdfData"].encode('utf-8')))

            booking.z_label_url = str(
                booking.fk_client_warehouse.client_warehouse_code) + "_" + booking.b_clientReference_RA_Numbers + "_" + str(
                booking.b_bookingID_Visual) + '.pdf'
            booking.save()
            request_type = "ALLIED GET LABEL"
            request_status = "SUCCESS"
            oneLog = Log(request_payload=data, request_status=request_status,
                         request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()

            results.append({"Created label ID": file_url})
        except KeyError:
            request_type = "ALLIED GET LABEL"
            request_status = "ERROR"
            oneLog = Log(request_payload=data, request_status=request_status,
                         request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()

            results.append({"Error": data0["errorMsg"]})

    except IndexError:
        results.append({"message": "Booking not found"})

    return results


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_label_allied(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]
        results = get_label_allied_fn(bid)

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


def get_label_st_fn(bid):
    results = []
    try:
        booking = Bookings.objects.filter(id=bid)[0]

        data = {}

        data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                    "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                    "accountPassword": "xab801a41e663b5cb889"}
        data['serviceProvider'] = "ST"
        data['consignmentNumber'] = booking.v_FPBookingNumber

        data['type'] = "# print"

        items = []
        confirmation_items = Api_booking_confirmation_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

        for ite in confirmation_items:
            temp_item = {"itemId": ite.api_item_id,
                         "packagingType": "PAL"
                         }
            items.append(temp_item)

        data['items'] = items

        items = []

        temp_item = {"branded": "_CMK0E6mwiMAAAFoYvcg7Ha9",
                     "branded": False,
                     "layout": "A4-1pp",
                     "leftOffset": 0,
                     "topOffset": 0,
                     "typeOfPost": "Express Post"
                     }
        items.append(temp_item)

        data['pageFormat'] = items

        # print('Payload(Get Label for ST): ', data)

        url = "http://52.62.102.72:8080/dme-api-sit/labelling/createlabel"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
        # print(s0)

        try:
            id = data0['stLabelRequestId']
            # id = "4c055984-2831-49b8-aca3-bf381a8315b8"
            # id = "f35af59f-6c05-4e5a-a397-4e689599c7ca"
            data['consignmentNumber'] = id

            data['labelType'] = "# print"

            url = "http://52.62.102.72:8080/dme-api-sit/labelling/getlabel"
            time.sleep(5)
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            # print(s0)

            booking.z_label_url = data0["url"]
            booking.save()
            request_type = "ST Label"
            request_status = "SUCCESS"
            oneLog = Log(request_payload=data, request_status=request_status,
                         request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()
            results.append({"Created label url": data0["url"]})
        except KeyError:
            try:
                request_type = "ST Label"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()
                results.append({"Error": data0["errorMsg"]})
            except KeyError:
                results.append({"Error": s0})

    except IndexError:
        results.append({"message": "Booking not found"})

    return results


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_label_st(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]
        results = get_label_st_fn(bid)

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def booking_allied(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]

        try:
            booking = Bookings.objects.filter(id=bid)[0]

            # print(booking.b_dateBookedDate)
            if booking.b_dateBookedDate is not None:
                return Response([{"Error": "Record has already booked."}])

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            if booking.booking_api_try_count == 0:
                booking.booking_api_start_TimeStamp = datetime.now()
                booking.booking_api_try_count = 1
                booking.save()
            else:
                booking.booking_api_try_count = int(booking.booking_api_try_count) + 1
                booking.save()

            data = {}
            data['spAccountDetails'] = {"accountCode": "SEATEM", "accountState": "NSW",
                                        "accountKey": "ce0d58fd22ae8619974958e65302a715"}
            data['serviceProvider'] = "ALLIED"
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data[
                'referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                     "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {
                "address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                "postCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
                "suburb": "" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                   "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                   "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                   "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {
                "address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                "postCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode,
                "state": "" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                "suburb": "" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                "sortCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:
                temp_item = {"dangerous": 0,
                             "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                             "length": 0 if line.e_dimLength is None else line.e_dimLength,
                             "quantity": 0 if line.e_qty is None else line.e_qty,
                             "volume": 0 if line.e_1_Total_dimCubicMeter is None else line.e_1_Total_dimCubicMeter,
                             "weight": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                             "width": 0 if line.e_dimWidth is None else line.e_dimWidth
                             }
                items.append(temp_item)

            data['items'] = items
            # print(data)

            url = "http://35.161.204.104:8081/dme-api/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            # print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0['consignmentNumber']
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0['consignmentNumber']
                booking.fk_fp_pickup_id = data0['requestId']
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.booking_api_end_TimeStamp = datetime.now()
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
                get_label_allied_fn(booking.id)
            except KeyError:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = "ALLIED BOOKING"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)



@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def pricing_allied(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]

        try:
            booking = Bookings.objects.filter(id=bid)[0]

            # print(booking.b_dateBookedDate)
            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            if booking.booking_api_try_count == 0:
                booking.booking_api_start_TimeStamp = datetime.now()
                booking.booking_api_try_count = 1
                booking.save()
            else:
                booking.booking_api_try_count = int(booking.booking_api_try_count) + 1
                booking.save()

            data = {}
            data['spAccountDetails'] = {"accountCode": "SEATEM", "accountState": "NSW",
                                        "accountKey": "ce0d58fd22ae8619974958e65302a715"}
            data['serviceProvider'] = "ALLIED"
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data[
                'referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                     "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {
                "address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                "postCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
                "suburb": "" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                   "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                   "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                   "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {
                "address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                "postCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode,
                "state": "" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                "suburb": "" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                "sortCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:
                temp_item = {"dangerous": 0,
                             "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                             "length": 0 if line.e_dimLength is None else line.e_dimLength,
                             "quantity": 0 if line.e_qty is None else line.e_qty,
                             "volume": 0 if line.e_1_Total_dimCubicMeter is None else line.e_1_Total_dimCubicMeter,
                             "weight": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                             "width": 0 if line.e_dimWidth is None else line.e_dimWidth
                             }
                items.append(temp_item)

            data['items'] = items
            # print(data)

            url = "http://35.161.204.104:8081/dme-api/pricing/calculateprice"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            # print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0['consignmentNumber']
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0['consignmentNumber']
                booking.fk_fp_pickup_id = data0['requestId']
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.booking_api_end_TimeStamp = datetime.now()
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
                get_label_allied_fn(booking.id)
            except KeyError:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = "ALLIED BOOKING"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def st_create_order(request):
    results = []
    date = literal_eval(request.body.decode('utf8'))
    date = date["date"]
    # # print('Date (Create Order for ST): ', datetime.now().strftime("%Y-%m-%d"))
    # print('Date (Create Order for ST): ', date)

    try:
        bookings = Bookings.objects.filter(vx_freight_provider="STARTRACK",
                                           puPickUpAvailFrom_Date=date,
                                           b_status="Booked")

        data = {}

        data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                    "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                    "accountPassword": "xab801a41e663b5cb889"}
        data['serviceProvider'] = "ST"
        data['paymentMethods'] = "CHARGE_TO_ACCOUNT"
        data['referenceNumber'] = "refer1"

        booking_numbers = []
        for booking in bookings:
            booking_numbers.append(booking.v_FPBookingNumber)

        data['consignmentNumber'] = booking_numbers

        # print('Payload(Create Order for ST): ', data)

        url = "http://52.62.102.72:8080/dme-api-sit/order/create"
        response0 = requests.post(url, params={}, json=data)
        response0 = response0.content.decode('utf8').replace("'", '"')
        data0 = json.loads(response0)
        s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
        # print(s0)

        try:
            results.append({"Order create Successfully ": data0["orderId"]})

            request_type = "Create Order"
            request_status = "SUCCESS"
            oneLog = Log(request_payload=data, request_status=request_status,
                         request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()
            data['orderId'] = data0["orderId"]
            for booking in bookings:
                booking.vx_fp_order_id = data['orderId']
                booking.save()

            summary_res = get_order_summary_fn(data0["orderId"])
            results.append(summary_res)

        except KeyError:
            try:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = "Create Order"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()
                results.append({"Error": data0["errorMsg"]})
            except KeyError:
                results.append({"Error": s0})

    except IndexError:
        results.append({"message": "Booking not found"})

    return Response(results)


def get_order_summary_fn(order_id):
    results = []

    data = {}

    data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                "accountPassword": "xab801a41e663b5cb889"}
    data['serviceProvider'] = "ST"
    data['orderId'] = order_id

    # print(data)

    url = "http://52.62.102.72:8080/dme-api-sit/order/summary"
    response0 = requests.post(url, params={}, json=data)
    response0 = response0.content.decode('utf8').replace("'", '"')
    data0 = json.loads(response0)
    s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
    # print(s0)
    try:
        file_name = "biopak_manifest_" + str(order_id) + '_' + str(datetime.now()) + '.pdf'
        file_url = '/var/www/html/dme_api/static/pdfs/' + file_name

        with open(os.path.expanduser(file_url), 'wb') as fout:
            fout.write(base64.decodestring(data0["pdfData"].encode('utf-8')))

        bookings = Bookings.objects.filter(vx_fp_order_id=order_id)
        for book in bookings:
            book.z_manifest_url = file_name
            book.save()

        return {"Success": "Manifest is created successfully."}

    except KeyError:

        return {"Error": data0["errorMsg"]}

    return results


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def get_order_summary(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]
        try:
            booking = Bookings.objects.filter(id=bid)[0]
            results.append(get_order_summary_fn(booking.vx_fp_order_id))

        except IndexError:
            results.append({"message": "Order is not created for this booking."})
    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def booking_st(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]

        try:
            booking = Bookings.objects.filter(id=bid)[0]

            if booking.b_status != 'Ready for booking':
                return Response([{"Error": "Booking is already booked."}])

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            data = {}
            data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                        "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                        "accountPassword": "xab801a41e663b5cb889"}
            data['serviceProvider'] = "ST"
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data[
                'referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "Rosie Stokeld" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                     "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "0267651109" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {
                "address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                "postCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
                "suburb": "" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "James Sam" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                   "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                   "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                   "phoneNumber": "0393920020" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {
                "address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                "postCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode,
                "state": "" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                "suburb": "" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                "sortCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:
                for i in range(line.e_qty):
                    temp_item = {"dangerous": 0,
                                 "itemId": "EXP",
                                 "packagingType": "PAL",
                                 "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                                 "length": 0 if line.e_dimLength is None else line.e_dimLength,
                                 "quantity": 0 if line.e_qty is None else line.e_qty,
                                 "volume": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                                 "weight": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                                 "width": 0 if line.e_dimWidth is None else line.e_dimWidth
                                 }
                    items.append(temp_item)

            data['items'] = items
            # print(data)

            url = "http://52.62.102.72:8080/dme-api-sit/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            # print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0['consignmentNumber']
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0['consignmentNumber']
                booking.fk_fp_pickup_id = data0['requestId']
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
                Api_booking_confirmation_lines.objects.filter(fk_booking_id=booking.pk_booking_id).delete()

                for item in data0['items']:
                    book_con = Api_booking_confirmation_lines(fk_booking_id=booking.pk_booking_id,
                                                              api_item_id=item["itemId"])
                    book_con.save()

                get_label_st_fn(booking.id)
            except KeyError:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = "ST BOOKING"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()
                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

        except TypeError:
            results.append({"message": "eqty is none"})


    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def edit_booking_st(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]

        try:
            booking = Bookings.objects.filter(id=bid)[0]

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            data = {}
            data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                        "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                        "accountPassword": "xab801a41e663b5cb889"}
            data['serviceProvider'] = "ST"
            data['consignmentNumber'] = booking.v_FPBookingNumber
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data[
                'referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "Rosie Stokeld" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                     "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "0267651109" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {
                "address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                "postCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                "state": "" if booking.pu_Address_State is None else booking.pu_Address_State,
                "suburb": "" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "James Sam" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                   "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                   "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                   "phoneNumber": "0393920020" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {
                "address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                "postCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode,
                "state": "" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                "suburb": "" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                "sortCode": "" if booking.de_To_Address_PostalCode is None else booking.de_To_Address_PostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:
                temp_item = {"dangerous": 0,
                             "itemId": "EXP",
                             "packagingType": "PAL",
                             "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                             "length": 0 if line.e_dimLength is None else line.e_dimLength,
                             "quantity": 0 if line.e_qty is None else line.e_qty,
                             "volume": 0 if line.e_1_Total_dimCubicMeter is None else line.e_1_Total_dimCubicMeter,
                             "weight": 0 if line.e_Total_KG_weight is None else line.e_Total_KG_weight,
                             "width": 0 if line.e_dimWidth is None else line.e_dimWidth
                             }
                items.append(temp_item)

            data['items'] = items
            # print(data)

            url = "http://52.62.102.72:8080/dme-api-sit/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            # print(s0)

            try:
                request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
                request_payload["apiUrl"] = url
                request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
                request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
                request_payload["trackingId"] = data0['consignmentNumber']
                request_type = "TRACKING"
                request_status = "SUCCESS"

                booking.v_FPBookingNumber = data0['consignmentNumber']
                booking.fk_fp_pickup_id = data0['requestId']
                booking.b_dateBookedDate = str(datetime.now())
                booking.b_status = "Booked"
                booking.b_error_Capture = ""
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
                Api_booking_confirmation_lines.objects.filter(fk_booking_id=booking.pk_booking_id).delete()

                for item in data0['items']:
                    book_con = Api_booking_confirmation_lines(fk_booking_id=booking.pk_booking_id,
                                                              api_item_id=item["itemId"])
                    book_con.save()

                get_label_st_fn(booking.id)
            except KeyError:
                booking.b_error_Capture = data0["errorMsg"]
                booking.save()
                request_type = "EDIT ST BOOKING"
                request_status = "ERROR"
                oneLog = Log(request_payload=data, request_status=request_status,
                             request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['POST'])
@permission_classes((AllowAny,))
def returnexcel(request):
    body = literal_eval(request.body.decode('utf8'))
    bookingIds = body["bookingIds"]

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="bookings_seaway.xlsx"'

    workbook = xlsxwriter.Workbook(response, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    worksheet.set_column(0, 12, width=24)
    bold = workbook.add_format({'bold': 1, 'align': 'left'})

    worksheet.write('A1', 'b_bookingID_Visual', bold)
    worksheet.write('B1', 'b_dateBookedDate', bold)
    worksheet.write('C1', 'puPickUpAvailFrom_Date', bold)
    worksheet.write('D1', 'pu_Address_State', bold)
    worksheet.write('E1', 'business_group', bold)
    worksheet.write('F1', 'deToCompanyName', bold)
    worksheet.write('G1', 'de_To_Address_Suburb', bold)
    worksheet.write('H1', 'de_To_Address_State', bold)
    worksheet.write('I1', 'de_To_Address_PostalCode', bold)
    worksheet.write('J1', 'b_client_sales_inv_num', bold)
    worksheet.write('K1', 'b_client_order_num', bold)
    worksheet.write('L1', 'v_FPBookingNumber', bold)
    worksheet.write('M1', 'b_status', bold)
    worksheet.write('N1', 's_21_Actual_Delivery_TimeStamp', bold)
    worksheet.write('O1', 'zc_pod_or_no_pod', bold)

    row = 1
    col = 0

    for id in bookingIds:
        booking = Bookings.objects.get(id=id)

        worksheet.write(row, col, booking.b_bookingID_Visual)

        if booking.b_dateBookedDate and booking.b_dateBookedDate:
            worksheet.write(row, col + 1, booking.b_dateBookedDate.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            worksheet.write(row, col + 1, "")

        if booking.puPickUpAvailFrom_Date and booking.puPickUpAvailFrom_Date:
            worksheet.write(row, col + 2, booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            worksheet.write(row, col + 2, "")

        worksheet.write(row, col + 3, booking.pu_Address_State)

        customer_group_name = ''
        customer_groups = Dme_utl_client_customer_group.objects.all()
        for customer_group in customer_groups:
          if customer_group.name_lookup.lower() in booking.deToCompanyName.lower():
            customer_group_name = customer_group.group_name

        worksheet.write(row, col + 4, customer_group_name)

        worksheet.write(row, col + 5, booking.deToCompanyName)
        worksheet.write(row, col + 6, booking.de_To_Address_Suburb)
        worksheet.write(row, col + 7, booking.de_To_Address_State)
        worksheet.write(row, col + 8, booking.de_To_Address_PostalCode)
        worksheet.write(row, col + 9, booking.b_client_sales_inv_num)
        worksheet.write(row, col + 10, booking.b_client_order_num)
        worksheet.write(row, col + 11, booking.v_FPBookingNumber)
        worksheet.write(row, col + 12, booking.b_status_API)

        if booking.s_21_Actual_Delivery_TimeStamp and booking.s_21_Actual_Delivery_TimeStamp:
            worksheet.write(row, col + 13, booking.s_21_Actual_Delivery_TimeStamp.strftime("%Y-%m-%d"))
        else:
            worksheet.write(row, col + 13, "")

        if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0) or (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
          worksheet.write(row, col + 14, "Y")
        else:
          worksheet.write(row, col + 14, "N")

        if settings.ENV == 'dev':
          if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0):
            worksheet.write_url(row, col + 15, 'http://3.105.62.128/static/pdfs/' + booking.z_pod_url, string=booking.z_pod_url)

          if (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
            worksheet.write_url(row, col + 16, 'http://3.105.62.128/static/pdfs/' + booking.z_pod_signed_url, string=booking.z_pod_signed_url)
        elif settings.ENV == 'prod':
          if (booking.z_pod_url is not None and len(booking.z_pod_url) > 0):
            worksheet.write_url(row, col + 15, 'http://13.55.64.102/static/pdfs/' + booking.z_pod_url, string=booking.z_pod_url)

          if (booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) > 0):
            worksheet.write_url(row, col + 16, 'http://13.55.64.102/static/pdfs/' + booking.z_pod_signed_url, string=booking.z_pod_signed_url)

        row += 1

    workbook.close()
    return response
    # body = literal_eval(request.body.decode('utf8'))
    # bookingIds = body["bookingIds"]

    # response = HttpResponse(content_type='application/vnd.ms-excel')
    # response['Content-Disposition'] = 'attachment; filename="bookings_seaway.xlsx"'

    # workbook = xlsxwriter.Workbook(response, {'in_memory': True})
    # worksheet = workbook.add_worksheet()
    # worksheet.set_column(0, 13, width=24)
    # bold = workbook.add_format({'bold': 1, 'align': 'left'})

    # worksheet.write('A1', 'b_bookingID_Visual', bold)
    # worksheet.write('B1', 'puPickUpAvailFrom_Date', bold)
    # worksheet.write('C1', 'b_dateBookedDate', bold)
    # worksheet.write('D1', 'puCompany', bold)
    # worksheet.write('E1', 'pu_Address_Suburb', bold)
    # worksheet.write('F1', 'pu_Address_State', bold)
    # worksheet.write('G1', 'pu_Address_PostalCode', bold)
    # worksheet.write('H1', 'deToCompanyName', bold)
    # worksheet.write('I1', 'de_To_Address_Suburb', bold)
    # worksheet.write('J1', 'de_To_Address_State', bold)
    # worksheet.write('K1', 'de_To_Address_PostalCode', bold)
    # worksheet.write('L1', 'b_clientReference_RA_Numbers', bold)
    # worksheet.write('M1', 'vx_freight_provider', bold)
    # worksheet.write('N1', 'vx_serviceName', bold)
    # worksheet.write('O1', 'v_FPBookingNumber', bold)
    # worksheet.write('P1', 'b_status', bold)
    # worksheet.write('Q1', 'b_status_API', bold)
    # worksheet.write('R1', 's_05_LatestPickUpDateTimeFinal', bold)
    # worksheet.write('S1', 's_06_LatestDeliveryDateTimeFinal', bold)
    # worksheet.write('T1', 's_20_Actual_Pickup_TimeStamp', bold)
    # worksheet.write('U1', 's_21_Actual_Delivery_TimeStamp', bold)
    # worksheet.write('V1', 'z_pod_url', bold)
    # worksheet.write('W1', 'z_pod_signed_url', bold)
    # worksheet.write('X1', 'vx_fp_pu_eta_time', bold)
    # worksheet.write('Y1', 'vx_fp_del_eta_time', bold)

    # row = 1
    # col = 0

    # for id in bookingIds:
    #     booking = Bookings.objects.get(id=id)
    #     worksheet.write(row, col, booking.b_bookingID_Visual)

    #     if booking.puPickUpAvailFrom_Date and booking.puPickUpAvailFrom_Date:
    #         worksheet.write(row, col + 1, booking.puPickUpAvailFrom_Date.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 1, "")

    #     if booking.b_dateBookedDate and booking.b_dateBookedDate:
    #         worksheet.write(row, col + 2, booking.b_dateBookedDate.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 2, "")

    #     worksheet.write(row, col + 3, booking.puCompany)
    #     worksheet.write(row, col + 4, booking.pu_Address_Suburb)
    #     worksheet.write(row, col + 5, booking.pu_Address_State)
    #     worksheet.write(row, col + 6, booking.pu_Address_PostalCode)
    #     worksheet.write(row, col + 7, booking.deToCompanyName)
    #     worksheet.write(row, col + 8, booking.de_To_Address_Suburb)
    #     worksheet.write(row, col + 9, booking.de_To_Address_State)
    #     worksheet.write(row, col + 10, booking.de_To_Address_PostalCode)
    #     worksheet.write(row, col + 11, booking.b_clientReference_RA_Numbers)
    #     worksheet.write(row, col + 12, booking.vx_freight_provider)
    #     worksheet.write(row, col + 13, booking.vx_serviceName)
    #     worksheet.write(row, col + 14, booking.v_FPBookingNumber)
    #     worksheet.write(row, col + 15, booking.b_status)
    #     worksheet.write(row, col + 16, booking.b_status_API)

    #     if booking.s_05_LatestPickUpDateTimeFinal and booking.s_05_LatestPickUpDateTimeFinal:
    #         worksheet.write(row, col + 17, booking.s_05_LatestPickUpDateTimeFinal.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 17, "")

    #     if booking.s_06_LatestDeliveryDateTimeFinal and booking.s_06_LatestDeliveryDateTimeFinal:
    #         worksheet.write(row, col + 18, booking.s_06_LatestDeliveryDateTimeFinal.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 18, "")

    #     if booking.s_20_Actual_Pickup_TimeStamp and booking.s_20_Actual_Pickup_TimeStamp:
    #         worksheet.write(row, col + 19, booking.s_20_Actual_Pickup_TimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 19, "")

    #     if booking.s_21_Actual_Delivery_TimeStamp and booking.s_21_Actual_Delivery_TimeStamp:
    #         worksheet.write(row, col + 20, booking.s_21_Actual_Delivery_TimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 20, "")

    #     worksheet.write(row, col + 21, booking.z_pod_url)
    #     worksheet.write(row, col + 22, booking.z_pod_signed_url)

    #     if booking.vx_fp_pu_eta_time and booking.vx_fp_pu_eta_time:
    #         worksheet.write(row, col + 23, booking.vx_fp_pu_eta_time.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 23, "")

    #     if booking.vx_fp_del_eta_time and booking.vx_fp_del_eta_time:
    #         worksheet.write(row, col + 24, booking.vx_fp_del_eta_time.strftime("%Y-%m-%d %H:%M:%S"))
    #     else:
    #         worksheet.write(row, col + 24, "")

    #     row += 1

    # workbook.close()
    # return response


@api_view(['GET'])
@permission_classes((AllowAny,))
def returntempexcel(request):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="bookings_seaway.xlsx"'

    workbook = xlsxwriter.Workbook(response, {'in_memory': True})

    bookings = Bookings.objects.filter(b_client_name="Seaway", b_status="Booked").order_by('fk_client_warehouse')

    worksheet = workbook.add_worksheet()

    worksheet.set_column(0, 14, width=20)
    bold = workbook.add_format({'bold': 1, 'align': 'left'})
    worksheet.write('A1', 'Warehouse Name', bold)
    worksheet.write('B1', 'b_client_name', bold)
    worksheet.write('C1', 'b_bookingID_Visual', bold)
    worksheet.write('D1', 'vx_freight_provider', bold)
    worksheet.write('E1', 'pk_booking_id', bold)
    worksheet.write('F1', 'v_FPBookingNumber', bold)
    worksheet.write('G1', 'vx_serviceName', bold)
    worksheet.write('H1', 'deToCompanyName', bold)
    worksheet.write('I1', 'de_To_Address_PostalCode', bold)
    worksheet.write('J1', 'b_status', bold)
    worksheet.write('K1', 'b_status_API', bold)
    worksheet.write('L1', 's_21_ActualDeliveryTimeStamp', bold)
    worksheet.write('M1', 'total_Cubic_Meter_override', bold)
    worksheet.write('N1', 'total_1_KG_weight_override', bold)
    worksheet.write('O1', 'total_lines_qty_override', bold)

    row = 1
    col = 0

    for booking in bookings:
        worksheet.write(row, col, booking.fk_client_warehouse.client_warehouse_code)
        worksheet.write(row, col + 1, booking.b_client_name)
        worksheet.write(row, col + 2, booking.b_bookingID_Visual)
        worksheet.write(row, col + 3, booking.vx_freight_provider)
        worksheet.write(row, col + 4, booking.pk_booking_id)
        worksheet.write(row, col + 5, booking.v_FPBookingNumber)
        worksheet.write(row, col + 6, booking.vx_serviceName)
        worksheet.write(row, col + 7, booking.deToCompanyName)
        worksheet.write(row, col + 8, booking.de_To_Address_PostalCode)
        worksheet.write(row, col + 9, booking.b_status)
        worksheet.write(row, col + 10, booking.b_status_API)
        if booking.s_21_ActualDeliveryTimeStamp and booking.s_21_ActualDeliveryTimeStamp:
            worksheet.write(row, col + 11, booking.s_21_ActualDeliveryTimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            worksheet.write(row, col + 11, "")
        worksheet.write(row, col + 12, booking.total_Cubic_Meter_override)
        worksheet.write(row, col + 13, booking.total_1_KG_weight_override)
        worksheet.write(row, col + 14, booking.total_lines_qty_override)

        row += 1

    workbook.close()
    return response


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def cancel_booking(request):
    results = []
    try:
        bid = literal_eval(request.body.decode('utf8'))
        bid = bid["booking_id"]
        booking = Bookings.objects.filter(id=bid)[0]

        if booking.b_status != "Closed":
            if booking.b_dateBookedDate is not None:
                data = {}
                data['spAccountDetails'] = {"accountCode": "00956684", "accountState": "NSW",
                                            "accountKey": "4a7a2e7d-d301-409b-848b-2e787fab17c9",
                                            "accountPassword": "xab801a41e663b5cb889"}
                data['serviceProvider'] = "ST"
                data['consignmentNumber'] = booking.v_FPBookingNumber

                url = "http://52.62.102.72:8080/dme-api-sit/booking/cancelconsignment"
                response0 = requests.delete(url, params={}, json=data)
                response0 = response0.content.decode('utf8').replace("'", '"')
                data0 = json.loads(response0)
                s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
                # print(s0)

                try:
                    a = data0["requestId"]
                    booking.b_status = "Closed"
                    booking.b_booking_Notes = "This booking has been closed vis Startrack API"
                    booking.save()
                    request_type = "CANCEL ST BOOKING"
                    request_status = "SUCCESS"
                    oneLog = Log(request_payload=data, request_status=request_status,
                                 request_type=request_type,
                                 response=response0, fk_booking_id=booking.id)
                    oneLog.save()

                    results.append({"message": "Booking canceled "})
                except KeyError:
                    request_type = "CANCEL ST BOOKING"
                    request_status = "ERROR"
                    oneLog = Log(request_payload=data, request_status=request_status,
                                 request_type=request_type,
                                 response=response0, fk_booking_id=booking.id)
                    oneLog.save()

                    results.append({"message": "Error while canceling "})
            else:
                results.append({"message": "Booking is not booked yet."})
        else:
            results.append({"message": "Booking is closed."})

    except IndexError:
        results.append({"message": "Booking not found."})

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)
