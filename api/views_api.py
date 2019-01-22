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

from .serializers_api import BOK_0_BookingKeysSerializer, BOK_1_headersSerializer, BOK_2_linesSerializer
from .models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines, Bookings, Booking_lines
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
							   deToAddressPostalCode=bok_1.b_059_b_del_address_postalcode,
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
	print("Response ",booking_list)
	for booking in booking_list:
		print("booking",booking)
		url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
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
def st_booking(request):
	booking_list = Bookings.objects.filter(b_bookingID_Visual="500002")  # add z_api_status_update_flag_500 check
	results = []
	# booking = booking_list[0]
	print("Response ",booking_list)
	for booking in booking_list:
		print("booking",booking)
		url = "http://52.39.202.126:8080/dme-api-sit/booking/bookconsignment"
		# data = {}

		# data["serviceProvider"] = "ST"
		# data["spAccountDetails"]["accountCode"]="10149943"
		# data["spAccountDetails"]["accountState"]="NSW"
		# data["spAccountDetails"]["accountPassword"]="x81775935aece65541c9"
		# data["spAccountDetails"]["accountKey"]= "d36fca86-53da-4db8-9a7d-3029975aa134"

		data = {
			"serviceProvider": "ST",
			"spAccountDetails":
			{
				"accountCode":"10149943",
				"accountState":"NSW",
				"accountPassword":"x81775935aece65541c9",
				"accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134"
			},

			"referenceNumber": booking.b_clientReference_RA_Numbers ,
			"bookedBy" :"Pete Walbolt",

			"pickupAddress" :
			{
				"companyName": booking.puCompany ,
				"contact": booking.pu_Contact_F_L_Name ,
				"emailAddress":booking.pu_Email,
				"instruction" : booking.pu_PickUp_Instructions_Contact,
				"phoneNumber" :booking.pu_Phone_Main ,
				"postalAddress" :
				{
					# "address1" : booking.pu_Address_Street_1 ,
					# "address2":booking.pu_Address_street_2,
					# "country" :  booking.pu_Address_Country,
					# "postCode" : "2340",
					# "sortCode" :  "2340",
					# "state" : booking.pu_Address_State,
				 # 	"suburb" :  booking.pu_Address_Suburb,

				 	"address1" :  "Ref: Returns 4 Tempo Pty Ltd. Fragile",
					"address2": "43 The Ringers Road",
					"country" :  "England",
					"postCode" : "2340",
					"sortCode" :  "2340",
					"state" : "NSW",
				 	"suburb" :  "Tamworth"
				}
			},
			"dropAddress": {
				"companyName":  booking.deToCompanyName ,
				"contact" :"James Sam",
				# "contact" :booking.de_Contact,
				"emailAddress" : booking.de_Email ,
				"instruction" :booking.de_to_Pick_Up_Instructions_Contact ,
				"phoneNumber" : booking.de_to_Phone_Main ,

				"postalAddress": {
					"address1" : "Door 13, Building 2",
					"address2" : "207 Sunshine Road",
					"country" : "England",
					"postCode" : "3012",
					"sortCode" : "3012" ,
					"state" : "VIC",
					"suburb":  "Tottenham"
				},


				# "postalAddress": {
				# 	"address1" : booking.de_To_Address_Street_1,
				# 	"address2" :booking.de_To_Address_Street_2 ,
				# 	"country" : booking.de_To_Address_Country,
				# 	"postCode" :booking.de_To_Address_PostalCode ,
				# 	"sortCode" : "3012" ,
				# 	"state" : booking.de_To_Address_State ,
				# 	"suburb": booking.de_To_Address_Suburb
				# },
			},
			"readyDate":"2026-07-12T09:11:27.000+0000",
			"serviceType":booking.v_service_Type_2,
			"items": []
		}

		print("booking id",int(booking.id))
		booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
		print("booking lines",booking_lines)
		# index = 0
		items = []
		for booking_line in booking_lines:
			print("booking line")
			item_data={
				# "itemId": booking.vx_serviceName,
				"itemId": "EXP",
				"dangerous": booking_line.e_dangerousGoods,
				"height": booking_line.e_dimHeight ,
				"length": booking_line.e_dimLength,
				"quantity":booking_line.e_qty,
				"volume":"10",
				"weight": booking_line.e_weightPerEach,
				"width": booking_line.e_dimWidth,
				"packagingType": "PAL"
			}
			data["items"].append(item_data)

		# data["items"].append(items)


			# index += 1



		# }

		print("data",data)

		req_data = json.dumps(data)
		print("req_data",req_data)


		request_timestamp = datetime.datetime.now()

		response0 = requests.post(url, params={}, json=req_data)
		print("Response ==> ",response0)
		response0 = response0.content.decode('utf8').replace("'", '"')
		data0 = json.loads(response0)
		s0 = json.dumps(data0, indent=4, sort_keys=True)  # Just for visual
		print(s0)

		# try:
		#     request_id = data0['requestId']
		#     request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
		#     request_payload["apiUrl"] = url
		#     request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
		#     request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
		#     request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
		#     request_type = "TRACKING"
		#     request_status = "SUCCESS"

		#     oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
		#                  response=response0, fk_booking_id=booking.id)
		#     oneLog.save()
		#     booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
		#     booking.save()

		#     results.append({"Created Log ID": oneLog.id})
		# except KeyError:
		#     results.append({"Error": "Too many request"})

	return Response("success")



@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def allied_tracking(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="ALLIED",
                                           z_api_issue_update_flag_500=1)  # add z_api_status_update_flag_500 check
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
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
def all_trigger(request):
    booking_list = Bookings.objects.filter(z_api_issue_update_flag_500=1)
    results = []

    for booking in booking_list:
        if booking.vx_freight_provider == "Allied" and booking.b_client_name == "Seaway":
            url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
            data = {}
            print("==============")
            print(booking.v_FPBookingNumber)
            print(booking.deToAddressPostalCode)
            print("==============")
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                           "destinationPostcode": booking.deToAddressPostalCode}]
            data['spAccountDetails'] = {"accountCode": "DELVME", "accountState": "NSW",
                                        "accountKey": "ce0d58fd22ae8619974958e65302a715"}
            data['serviceProvider'] = "ALLIED"

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
                try:
                    booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                    booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                    if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Shipment has been delivered.':
                        booking.s_21_ActualDeliveryTimeStamp = datetime.datetime.now()

                    booking.save()
                except IndexError:
                    print("asd")

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})
        elif booking.vx_freight_provider == "STARTRACK":
            url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
            data = {}
            print("==============")
            print(booking.v_FPBookingNumber)
            data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber}]
            data['spAccountDetails'] = {"accountCode": "10149943", "accountState": "NSW",
                                        "accountPassword": "x81775935aece65541c9",
                                        "accountKey": "d36fca86-53da-4db8-9a7d-3029975aa134"}
            data['serviceProvider'] = "ST"

            print(data)
            print("==============")
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
                try:
                    booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                    booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                    if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Shipment has been delivered.':
                        booking.s_21_ActualDeliveryTimeStamp = datetime.datetime.now()
                    booking.save()
                except IndexError:
                    print("asd")

                results.append({"Created Log ID": oneLog.id})
            except KeyError:
                results.append({"Error": "Too many request"})

    return Response(results)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def trigger_allied(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="Allied",
                                           z_api_issue_update_flag_500=1, b_client_name="Seaway", b_status_API__isnull=True)
    results = []

    for booking in booking_list:
        url = "http://35.161.204.104:8081/dme-api/tracking/trackconsignment"
        data = {}
        print("==============")
        print(booking.v_FPBookingNumber)
        print(booking.deToAddressPostalCode)
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.deToAddressPostalCode}]
        data['spAccountDetails'] = {"accountCode": "DELVME", "accountState": "NSW",
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
            request_type = "TRACKING"
            request_status = "SUCCESS"

            oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                         response=response0, fk_booking_id=booking.id)
            oneLog.save()
            try:
                booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Shipment has been delivered.':
                    booking.s_21_ActualDeliveryTimeStamp = datetime.datetime.now()

                booking.save()
                print("yes")
            except IndexError:
                print("no")

            print("==============")
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
        url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
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
            try:
                booking.b_status_API = data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status']
                booking.z_lastStatusAPI_ProcessedTimeStamp = datetime.datetime.now()
                if data0['consignmentTrackDetails'][0]['consignmentStatuses'][0]['status'] == 'Shipment has been delivered.':
                    booking.s_21_ActualDeliveryTimeStamp = datetime.datetime.now()

                booking.save()
            except IndexError:
                print("asd")

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
        url = "http://52.39.202.126:8080/dme-api-sit/tracking/trackconsignment"
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
def get_label_allied(request):
    booking_list = Bookings.objects.filter(vx_freight_provider="Allied",
                                           z_api_issue_update_flag_500=1)
    results = []

    for booking in booking_list:
        url = "http://52.39.202.126:8080/dme-api-sit/labelling/getlabel"
        data = {}
        print("==============")
        print(booking.v_FPBookingNumber)
        print(booking.deToAddressPostalCode)
        print("==============")
        data['consignmentDetails'] = [{"consignmentNumber": booking.v_FPBookingNumber,
                                       "destinationPostcode": booking.deToAddressPostalCode}]
        data['spAccountDetails'] = {"accountCode": "DELVME", "accountState": "NSW",
                                    "accountKey": "ce0d58fd22ae8619974958e65302a715"}
        data['serviceProvider'] = "ALLIED"

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

            results.append({"Created Log ID": oneLog.id})
        except KeyError:
            results.append({"Error": "Too many request"})

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

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            data = {}
            data['spAccountDetails'] = {"accountCode": "SEANSW", "accountState": "NSW",
                                        "accountKey": "11e328f646051c3decc4b2bb4584530b"}
            data['serviceProvider'] = "ALLIED"
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data['referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                        "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {"address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                                                      "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                                        "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                                     "postCode":"" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                                     "state":"" if booking.pu_Address_State is None else booking.pu_Address_State,
                                     "suburb":"" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                                     "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                        "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                     "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                     "phoneNumber": "" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {"address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                                                      "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                                        "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                                     "postCode":"" if booking.deToAddressPostalCode is None else booking.deToAddressPostalCode,
                                     "state":"" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                                     "suburb":"" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                                     "sortCode": "" if booking.deToAddressPostalCode is None else booking.deToAddressPostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:

                temp_item = {"dangerous": 0,
                                "height": 0 if line.e_dimHeight is None else line.e_dimHeight,
                                "length": 0 if line.e_dimLength is None else line.e_dimLength,
                                "quantity": 0 if line.e_qty is None else line.e_qty,
                                "volume": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                                "weight": 0 if line.e_weightPerEach is None else line.e_weightPerEach,
                                "width": 0 if line.e_dimWidth is None else line.e_dimWidth
                             }
                items.append(temp_item)

            data['items'] = items
            print(data)

            url = "http://52.39.202.126:8080/dme-api-sit/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            print(s0)

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
                booking.b_dateBookedDate = str(datetime.datetime.now())
                booking.b_status = "Booked"
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
            except KeyError:
                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

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

            if booking.pu_Address_State is None or not booking.pu_Address_State:
                return Response([{"Error": "State for pickup postal address is required."}])

            if booking.pu_Address_Suburb is None or not booking.pu_Address_Suburb:
                return Response([{"Error": "suburb name for pickup postal address is required."}])

            data = {}
            data['spAccountDetails'] = {"accountCode": "00251522", "accountState": "NSW",
                                        "accountKey": "71eb98b2-fa8d-4a38-b1b7-6fb2a5c5c486",
                                        "accountPassword": "x9083d2fed4d50aa2ad5"}
            data['serviceProvider'] = "ST"
            data['readyDate'] = "" if booking.puPickUpAvailFrom_Date is None else str(booking.puPickUpAvailFrom_Date)
            data['referenceNumber'] = "" if booking.b_clientReference_RA_Numbers is None else booking.b_clientReference_RA_Numbers
            data['serviceType'] = "R" if booking.vx_serviceName is None else 'R'
            data['bookedBy'] = "Mr.CharlieBrown"
            data['pickupAddress'] = {"companyName": "" if booking.puCompany is None else booking.puCompany,
                                     "contact": "Rosie Stokeld" if booking.pu_Contact_F_L_Name is None else booking.pu_Contact_F_L_Name,
                                        "emailAddress": "" if booking.pu_Email is None else booking.pu_Email,
                                     "instruction": "" if booking.pu_PickUp_Instructions_Contact is None else booking.pu_PickUp_Instructions_Contact,
                                     "phoneNumber": "0267651109" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['pickupAddress']["postalAddress"] = {"address1": "" if booking.pu_Address_Street_1 is None else booking.pu_Address_Street_1,
                                                      "address2": "" if booking.pu_Address_street_2 is None else booking.pu_Address_street_2,
                                        "country": "" if booking.pu_Address_Country is None else booking.pu_Address_Country,
                                     "postCode":"" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode,
                                     "state":"" if booking.pu_Address_State is None else booking.pu_Address_State,
                                     "suburb":"" if booking.pu_Address_Suburb is None else booking.pu_Address_Suburb,
                                     "sortCode": "" if booking.pu_Address_PostalCode is None else booking.pu_Address_PostalCode}

            data['dropAddress'] = {"companyName": "" if booking.deToCompanyName is None else booking.deToCompanyName,
                                   "contact": "James Sam" if booking.de_to_Contact_F_LName is None else booking.de_to_Contact_F_LName,
                                        "emailAddress": "" if booking.de_Email is None else booking.de_Email,
                                     "instruction": "" if booking.de_to_Pick_Up_Instructions_Contact is None else booking.de_to_Pick_Up_Instructions_Contact,
                                     "phoneNumber": "0393920020" if booking.pu_Phone_Main is None else booking.pu_Phone_Main}
            data['dropAddress']["postalAddress"] = {"address1": "" if booking.de_To_Address_Street_1 is None else booking.de_To_Address_Street_1,
                                                      "address2": "" if booking.de_To_Address_Street_2 is None else booking.de_To_Address_Street_2,
                                        "country": "" if booking.de_To_Address_Country is None else booking.de_To_Address_Country,
                                     "postCode":"" if booking.deToAddressPostalCode is None else booking.deToAddressPostalCode,
                                     "state":"" if booking.de_To_Address_State is None else booking.de_To_Address_State,
                                     "suburb":"" if booking.de_To_Address_Suburb is None else booking.de_To_Address_Suburb,
                                     "sortCode": "" if booking.deToAddressPostalCode is None else booking.deToAddressPostalCode}

            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

            items = []

            for line in booking_lines:

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
            print(data)

            url = "http://52.39.202.126:8080/dme-api-sit/booking/bookconsignment"
            response0 = requests.post(url, params={}, json=data)
            response0 = response0.content.decode('utf8').replace("'", '"')
            data0 = json.loads(response0)
            s0 = json.dumps(data0, indent=4, sort_keys=True, default=str)  # Just for visual
            print(s0)

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
                booking.b_dateBookedDate = str(datetime.datetime.now())
                booking.b_status = "Booked"
                booking.save()

                oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type,
                             response=response0, fk_booking_id=booking.id)
                oneLog.save()

                results.append({"Created Booking ID": data0['consignmentNumber']})
            except KeyError:
                results.append({"Error": data0["errorMsg"]})

        except IndexError:
            results.append({"message": "Booking not found"})

    except SyntaxError:
        results.append({"message": "booking id is required"})

    return Response(results)


@api_view(['GET'])
@permission_classes((AllowAny,))
def returnexcel(request):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="bookings_seaway.xlsx"'

    workbook = xlsxwriter.Workbook(response, {'in_memory': True})

    bookings = Bookings.objects.filter(b_client_name="Seaway")

    worksheet = workbook.add_worksheet()

    worksheet.set_column(0, 10, width=20)
    bold = workbook.add_format({'bold': 1, 'align': 'left'})
    worksheet.write('A1', 'z_CreatedTimestamp', bold)
    worksheet.write('B1', 'b_client_name', bold)
    worksheet.write('C1', 'b_bookingID_Visual', bold)
    worksheet.write('D1', 'vx_freight_provider', bold)
    worksheet.write('E1', 'v_FPBookingNumber', bold)
    worksheet.write('F1', 'vx_serviceName', bold)
    worksheet.write('G1', 'deToCompanyName', bold)
    worksheet.write('H1', 'deToAddressPostalCode', bold)
    worksheet.write('I1', 'b_status', bold)
    worksheet.write('J1', 'b_status_API', bold)
    worksheet.write('K1', 's_21_ActualDeliveryTimeStamp', bold)

    row = 1
    col = 0

    for booking in bookings:
        worksheet.write(row, col, booking.z_CreatedTimestamp.strftime("%Y-%m-%d %H:%M:%S"))
        worksheet.write(row, col + 1, booking.b_client_name)
        worksheet.write(row, col + 2, booking.b_bookingID_Visual)
        worksheet.write(row, col + 3, booking.vx_freight_provider)
        worksheet.write(row, col + 4, booking.v_FPBookingNumber)
        worksheet.write(row, col + 5, booking.vx_serviceName)
        worksheet.write(row, col + 6, booking.deToCompanyName)
        worksheet.write(row, col + 7, booking.deToAddressPostalCode)
        worksheet.write(row, col + 8, booking.b_status)
        worksheet.write(row, col + 9, booking.b_status_API)
        worksheet.write(row, col + 10, booking.s_21_ActualDeliveryTimeStamp.strftime("%Y-%m-%d %H:%M:%S"))
        row += 1

    workbook.close()
    return response
