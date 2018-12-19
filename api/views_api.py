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

from api.serializers_api import BOK_0_BookingKeysSerializer, BOK_1_headersSerializer, BOK_2_linesSerializer
from pages.models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines, Bookings
from api.models import Log

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
    url = "http://52.39.202.126:8080/dme-api/tracking/trackconsignment"
    data = literal_eval(request.body.decode('utf8'))
    request_timestamp = datetime.datetime.now()

    response0 = requests.post(url, params={}, json=data)
    response0 = response0.content.decode('utf8').replace("'", '"')
    data0 = json.loads(response0)
    s0 = json.dumps(data0, indent=4, sort_keys=True)

    try:
        request_id = data0['requestId']
        request_payload = {"apiUrl": '', 'accountCode': '', 'authKey': '', 'trackingId': ''};
        request_payload["apiUrl"] = url
        request_payload["accountCode"] = data["spAccountDetails"]["accountCode"]
        request_payload["authKey"] = data["spAccountDetails"]["accountKey"]
        request_payload["trackingId"] = data["consignmentDetails"][0]["consignmentNumber"]
        request_type = "TRACKING"
        request_status = "SUCCESS"
        booking = Bookings.objects.get(v_FPBookingNumber=request_payload["trackingId"])
        fk_booking_id = booking

        oneLog = Log(request_payload=request_payload, request_status=request_status, request_type=request_type, response=response0, fk_booking_id=fk_booking_id)
        oneLog.save()

        return Response({"Created Log ID": oneLog.id})
    except KeyError:
        return Response(data0)
