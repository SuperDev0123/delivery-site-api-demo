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
