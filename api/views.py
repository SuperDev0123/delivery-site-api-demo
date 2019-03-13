from django.shortcuts import render
from django.core import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, views, status, authentication, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, action
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse, JsonResponse, QueryDict
from django.db.models import Q
from wsgiref.util import FileWrapper
from datetime import datetime, date, timedelta
from time import gmtime, strftime
from django.utils import timezone
import pytz
import os
import io
import json
import zipfile
import uuid

from .serializers import *
from .models import *
from .utils import clearFileCheckHistory, getFileCheckHistory, save2Redis

class UserViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def username(self, request, format=None):
        user_id = self.request.user.id
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()
        
        if dme_employee is not None:
            return JsonResponse({'username': request.user.username, 'clientname': 'dme'})
        else:
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
            client = DME_clients.objects.get(pk_id_dme_client=client_employee.fk_id_dme_client_id)
            return JsonResponse({'username': request.user.username, 'clientname': client.company_name})

    @action(detail=False, methods=['get'])
    def get_user_date_filter_field(self, requst, pk=None):
        user_id = self.request.user.id
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            return JsonResponse({'user_date_filter_field': 'z_CreatedTimestamp'})
        else:
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
            client = DME_clients.objects.get(pk_id_dme_client=client_employee.fk_id_dme_client_id)
            return JsonResponse({'user_date_filter_field': client.client_filter_date_field})

class BookingsViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer
    
    @action(detail=False, methods=['get'])
    def get_bookings(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.select_related().filter(pk_id_dme_client = int(client_employee.fk_id_dme_client_id)).first()

        start_date = self.request.query_params.get('startDate', None)
        if start_date == '*':
            search_type = 'ALL'
        else:
            search_type = 'FILTER'
            end_date = self.request.query_params.get('endDate', None)

        if search_type == 'FILTER':
            first_date = datetime.strptime(start_date, '%Y-%m-%d')
            last_date = (datetime.strptime(end_date, '%Y-%m-%d')+timedelta(days=1))
        warehouse_id = self.request.query_params.get('warehouseId', None)
        sort_field = self.request.query_params.get('sortField', None)
        column_filters = json.loads(self.request.query_params.get('columnFilters', None))
        prefilter = json.loads(self.request.query_params.get('prefilterInd', None))
        simple_search_keyword = self.request.query_params.get('simpleSearchKeyword', None)
        # item_count_per_page = self.request.query_params.get('itemCountPerPage', 10)
        
        if user_type == 'CLIENT':
            print('@01 - Client filter: ', client.dme_account_num)
        else:
            print('@01 - DME user')

        if start_date == '*':
            print('@02 - Date filter: ', start_date)
        else:    
            print('@02 - Date filter: ', start_date, end_date, first_date, last_date)

        print('@03 - Warehouse ID filter: ', warehouse_id)
        print('@04 - Sort field: ', sort_field)

        if user_type == 'CLIENT':
            print('@05 - Company name: ', client.company_name)
        else:
            print('@05 - Company name: DME')
        
        print('@06 - Prefilter: ', prefilter)
        print('@07 - Simple search keyword: ', simple_search_keyword)

        # DME & Client filter
        if user_type == 'DME':
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == 'company':
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == 'warehouse':
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)

        if search_type == 'FILTER':
            # Date filter
            if user_type == 'DME':
                queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
            else:
                if client.company_name  == 'Seaway':
                    queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
                elif client.company_name == 'BioPak':
                    queryset = queryset.filter(puPickUpAvailFrom_Date__range=(first_date, last_date))
                
        # Warehouse filter
        if int(warehouse_id) is not 0:
            queryset = queryset.filter(fk_client_warehouse=int(warehouse_id))

        if len(simple_search_keyword) > 0:
            queryset = queryset.filter(
                Q(b_bookingID_Visual__icontains=simple_search_keyword) | 
                Q(puPickUpAvailFrom_Date__icontains=simple_search_keyword) | 
                Q(puCompany__icontains=simple_search_keyword) | 
                Q(pu_Address_Suburb__icontains=simple_search_keyword) |
                Q(pu_Address_State__icontains=simple_search_keyword) |
                Q(pu_Address_PostalCode__icontains=simple_search_keyword) |
                Q(deToCompanyName__icontains=simple_search_keyword) |
                Q(de_To_Address_Suburb__icontains=simple_search_keyword) |
                Q(de_To_Address_State__icontains=simple_search_keyword) |
                Q(de_To_Address_PostalCode__icontains=simple_search_keyword) |
                Q(b_clientReference_RA_Numbers__icontains=simple_search_keyword) | 
                Q(vx_freight_provider__icontains=simple_search_keyword) | 
                Q(vx_serviceName__icontains=simple_search_keyword) | 
                Q(v_FPBookingNumber__icontains=simple_search_keyword) | 
                Q(b_status__icontains=simple_search_keyword) | 
                Q(b_status_API__icontains=simple_search_keyword) | 
                Q(s_05_LatestPickUpDateTimeFinal__icontains=simple_search_keyword) | 
                Q(s_06_LatestDeliveryDateTimeFinal__icontains=simple_search_keyword) | 
                Q(s_20_Actual_Pickup_TimeStamp__icontains=simple_search_keyword) |
                Q(s_21_Actual_Delivery_TimeStamp__icontains=simple_search_keyword))
        else:
            # Column filter
            try:
                column_filter = column_filters['b_bookingID_Visual']
                queryset = queryset.filter(b_bookingID_Visual__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['b_dateBookedDate']
                queryset = queryset.filter(b_dateBookedDate__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['puPickUpAvailFrom_Date']
                queryset = queryset.filter(puPickUpAvailFrom_Date__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['puCompany']
                queryset = queryset.filter(puCompany__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['pu_Address_Suburb']
                queryset = queryset.filter(pu_Address_Suburb__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['pu_Address_State']
                queryset = queryset.filter(pu_Address_State__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['pu_Address_PostalCode']
                queryset = queryset.filter(pu_Address_PostalCode__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['deToCompanyName']
                queryset = queryset.filter(deToCompanyName__icontains=column_filter)
            except KeyError:
                column_filter = ''
                
            try:
                column_filter = column_filters['de_To_Address_Suburb']
                queryset = queryset.filter(de_To_Address_Suburb__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['de_To_Address_State']
                queryset = queryset.filter(de_To_Address_State__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['de_To_Address_PostalCode']
                queryset = queryset.filter(de_To_Address_PostalCode__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['b_clientReference_RA_Numbers']
                queryset = queryset.filter(b_clientReference_RA_Numbers__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['vx_freight_provider']
                queryset = queryset.filter(vx_freight_provider__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['vx_serviceName']
                queryset = queryset.filter(vx_serviceName__icontains=column_filter)
            except KeyError:
                column_filter = ''
                
            try:
                column_filter = column_filters['v_FPBookingNumber']
                queryset = queryset.filter(v_FPBookingNumber__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['b_status']
                queryset = queryset.filter(b_status__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['b_status_API']
                queryset = queryset.filter(b_status_API__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['s_05_LatestPickUpDateTimeFinal']
                queryset = queryset.filter(s_05_LatestPickUpDateTimeFinal__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['s_06_LatestDeliveryDateTimeFinal']
                queryset = queryset.filter(s_06_LatestDeliveryDateTimeFinal__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['s_20_Actual_Pickup_TimeStamp']
                queryset = queryset.filter(s_20_Actual_Pickup_TimeStamp__icontains=column_filter)
            except KeyError:
                column_filter = ''

            try:
                column_filter = column_filters['s_21_Actual_Delivery_TimeStamp']
                queryset = queryset.filter(s_21_Actual_Delivery_TimeStamp__icontains=column_filter)
            except KeyError:
                column_filter = ''

        # Prefilter count
        errors_to_correct = 0
        missing_labels = 0
        to_manifest = 0
        to_process = 0
        closed = 0

        for booking in queryset:
            if booking.b_error_Capture is not None and len(booking.b_error_Capture) > 0:
                errors_to_correct += 1
            if booking.z_label_url is None or len(booking.z_label_url) == 0:
                missing_labels += 1
            if booking.b_status == 'Booked':
                to_manifest += 1
            if booking.b_status == 'Ready to booking':
                to_process += 1
            if booking.b_status == 'Closed':
                closed += 1

        # Prefilter 0 -> all, 1 -> errors_to_correct
        if prefilter == 1:
            queryset = queryset.exclude(b_error_Capture__isnull=True).exclude(b_error_Capture__exact='')
        if prefilter == 2:
            queryset = queryset.filter(Q(z_label_url__isnull=True) | Q(z_label_url__exact=''))
        elif prefilter == 3:
            queryset = queryset.filter(b_status__icontains='Booked')
        elif prefilter == 4:
            queryset = queryset.filter(b_status__icontains='Ready to booking')
        elif prefilter == 5:
            queryset = queryset.filter(b_status__icontains='Closed')

        # Sort
        if sort_field is None:
            queryset = queryset.order_by('id')
        else:
            queryset = queryset.order_by(sort_field)

        # Count
        bookings_cnt = queryset.count()

        # bookings = queryset[0:int(item_count_per_page)]
        bookings = queryset
        ret_data = [];

        for booking in bookings:
            ret_data.append({
                'id': booking.id, 
                'b_bookingID_Visual': booking.b_bookingID_Visual, 
                'b_dateBookedDate': booking.b_dateBookedDate, 
                'puPickUpAvailFrom_Date': booking.puPickUpAvailFrom_Date, 
                'b_clientReference_RA_Numbers': booking.b_clientReference_RA_Numbers, 
                'b_status': booking.b_status, 
                'vx_freight_provider': booking.vx_freight_provider, 
                'v_FPBookingNumber': booking.v_FPBookingNumber,
                'vx_serviceName': booking.vx_serviceName, 
                's_05_LatestPickUpDateTimeFinal': booking.s_05_LatestPickUpDateTimeFinal, 
                's_06_LatestDeliveryDateTimeFinal': booking.s_06_LatestDeliveryDateTimeFinal, 
                'puCompany': booking.puCompany,
                'deToCompanyName': booking.deToCompanyName,
                'z_label_url': booking.z_label_url,
                'b_error_Capture': booking.b_error_Capture,
                'z_downloaded_shipping_label_timestamp': booking.z_downloaded_shipping_label_timestamp,
                'pk_booking_id': booking.pk_booking_id,
                'pu_Address_street_1': booking.pu_Address_Street_1,
                'pu_Address_street_2': booking.pu_Address_street_2,
                'pu_Address_Suburb': booking.pu_Address_Suburb,
                'pu_Address_City': booking.pu_Address_City,
                'pu_Address_State': booking.pu_Address_State,
                'pu_Address_PostalCode': booking.pu_Address_PostalCode,
                'pu_Address_Country': booking.pu_Address_Country,
                'de_To_Address_street_1': booking.de_To_Address_Street_1,
                'de_To_Address_street_2': booking.de_To_Address_Street_2,
                'de_To_Address_Suburb': booking.de_To_Address_Suburb,
                'de_To_Address_City': booking.de_To_Address_City,
                'de_To_Address_State': booking.de_To_Address_State,
                'de_To_Address_PostalCode': booking.de_To_Address_PostalCode,
                'de_To_Address_Country': booking.de_To_Address_Country,
                's_20_Actual_Pickup_TimeStamp': booking.s_20_Actual_Pickup_TimeStamp,
                's_21_Actual_Delivery_TimeStamp': booking.s_21_Actual_Delivery_TimeStamp,
                'b_status_API': booking.b_status_API,
                'z_downloaded_pod_timestamp': booking.z_downloaded_pod_timestamp,
                'z_pod_url': booking.z_pod_url,
                'z_pod_signed_url': booking.z_pod_signed_url,
            })
        
        return JsonResponse({
            'bookings': ret_data, 'count': bookings_cnt, 
            'errors_to_correct': errors_to_correct, 'to_manifest': to_manifest, 
            'missing_labels': missing_labels, 'to_process': to_process, 
            'closed': closed})

    @action(detail=True, methods=['put'])
    def update_booking(self, request, pk, format=None):
        booking = Bookings.objects.get(pk=pk)
        serializer = BookingSerializer(booking, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BookingViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer
    
    @action(detail=False, methods=['get'])
    def get_booking(self, request, format=None):
        idBookingNumber = request.GET['id']
        filterName = request.GET['filter']
        user_id = request.user.id

        try:
            dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

            if dme_employee is not None:
                user_type = 'DME'
            else:
                user_type = 'CLIENT'

            if user_type == 'DME':
                queryset = Bookings.objects.all()
            else:
                client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()

                if client_employee is None:
                    return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})

                client_employee_role = client_employee.get_role()
                client = DME_clients.objects.get(pk_id_dme_client=client_employee.fk_id_dme_client_id)

                if client is None:
                    return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})
            
                if client_employee_role == 'company':
                    queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
                elif client_employee_role == 'warehouse':
                    employee_warehouse_id = client_employee.warehouse_id
                    queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)
            
            if filterName == 'dme':
                booking = queryset.get(b_bookingID_Visual=idBookingNumber)
            elif filterName == 'con':
                booking = queryset.filter(v_FPBookingNumber=idBookingNumber).first()
            elif filterName == 'id':
                booking = queryset.get(id=idBookingNumber)
            else:
                return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})

            if booking is not None:
                nextBooking = (queryset.filter(id__gt=booking.id).order_by('id').first())
                prevBooking = (queryset.filter(id__lt=booking.id).order_by('-id').first())
                nextBookingId = 0
                prevBookingId = 0

                if nextBooking is not None:
                    nextBookingId = nextBooking.id
                if prevBooking is not None:
                    prevBookingId = prevBooking.id

                return_data = []

                if booking is not None:
                    return_data = {
                        'id': booking.id,
                        'puCompany': booking.puCompany,
                        'pu_Address_Street_1': booking.pu_Address_Street_1,
                        'pu_Address_street_2': booking.pu_Address_street_2,
                        'pu_Address_PostalCode': booking.pu_Address_PostalCode,
                        'pu_Address_Suburb': booking.pu_Address_Suburb,
                        'pu_Address_Country': booking.pu_Address_Country,
                        'pu_Contact_F_L_Name': booking.pu_Contact_F_L_Name,
                        'pu_Phone_Main': booking.pu_Phone_Main,
                        'pu_Email': booking.pu_Email,
                        'de_To_Address_Street_1': booking.de_To_Address_Street_1,
                        'de_To_Address_Street_2':booking.de_To_Address_Street_2,
                        'de_To_Address_PostalCode': booking.de_To_Address_PostalCode,
                        'de_To_Address_Suburb': booking.de_To_Address_Suburb,
                        'de_To_Address_Country': booking.de_To_Address_Country,
                        'de_to_Contact_F_LName': booking.de_to_Contact_F_LName,
                        'de_to_Phone_Main':booking.de_to_Phone_Main,
                        'de_Email': booking.de_Email,
                        'deToCompanyName': booking.deToCompanyName, 
                        'b_bookingID_Visual': booking.b_bookingID_Visual,
                        'v_FPBookingNumber': booking.v_FPBookingNumber, 
                        'pk_booking_id': booking.pk_booking_id,
                        'vx_freight_provider': booking.vx_freight_provider,
                        'z_label_url': booking.z_label_url,
                        'pu_Address_State': booking.pu_Address_State,
                        'de_To_Address_State': booking.de_To_Address_State,
                        'b_status': booking.b_status,
                        'b_dateBookedDate': booking.b_dateBookedDate,
                        's_20_Actual_Pickup_TimeStamp': booking.s_20_Actual_Pickup_TimeStamp,
                        's_21_Actual_Delivery_TimeStamp': booking.s_21_Actual_Delivery_TimeStamp,
                        'b_client_name': booking.b_client_name,
                        'b_client_warehouse_code': booking.b_client_warehouse_code,
                        'b_clientPU_Warehouse': booking.b_clientPU_Warehouse,
                        'booking_Created_For': booking.booking_Created_For,
                        'booking_Created_For_Email': booking.booking_Created_For_Email,
                        'vx_fp_pu_eta_time': booking.vx_fp_pu_eta_time,
                        'vx_fp_del_eta_time': booking.vx_fp_del_eta_time,
                        'b_clientReference_RA_Numbers': booking.b_clientReference_RA_Numbers,
                        'de_to_Pick_Up_Instructions_Contact': booking.de_to_Pick_Up_Instructions_Contact,
                        'de_to_PickUp_Instructions_Address': booking.de_to_PickUp_Instructions_Address,
                        'pu_pickup_instructions_address': booking.pu_pickup_instructions_address,
                        'pu_PickUp_Instructions_Contact': booking.pu_PickUp_Instructions_Contact,
                        'vx_freight_provider': booking.vx_freight_provider,
                        'vx_serviceName': booking.vx_serviceName,
                        'consignment_label_link': booking.consignment_label_link,
                        's_02_Booking_Cutoff_Time': booking.s_02_Booking_Cutoff_Time,
                        'puPickUpAvailFrom_Date': booking.puPickUpAvailFrom_Date,
                        'z_CreatedTimestamp': booking.z_CreatedTimestamp,
                        'b_dateBookedDate': booking.b_dateBookedDate,
                        'total_lines_qty_override': booking.total_lines_qty_override,
                        'total_1_KG_weight_override': booking.total_1_KG_weight_override,
                        'total_Cubic_Meter_override': booking.total_Cubic_Meter_override,
                        'b_status_API': booking.b_status_API,
                    }
                    return JsonResponse({'booking': return_data, 'nextid': nextBookingId, 'previd': prevBookingId})
            else:
                return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})
        except Bookings.DoesNotExist:
            return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})

    @action(detail=True, methods=['post'])
    def post_booking(self, request, pk, format=None):
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def duplicate_booking(self, request, format=None):
        switch_info = request.GET['switchInfo']
        dup_line_and_linedetail = request.GET['dupLineAndLineDetail']
        booking_id = request.GET['bookingId']
        user_id = request.user.id

        booking = Bookings.objects.get(id=booking_id)

        if switch_info == 'true':
            newBooking = {
                'b_bookingID_Visual': Bookings.get_max_b_bookingID_Visual() + 1,
                'fk_client_warehouse': booking.fk_client_warehouse_id,
                'b_client_warehouse_code': booking.b_client_warehouse_code,
                'b_clientPU_Warehouse': booking.b_clientPU_Warehouse,
                'b_client_name': booking.b_client_name,
                'puCompany': booking.deToCompanyName,
                'pu_Address_Street_1': booking.de_To_Address_Street_1,
                'pu_Address_street_2': booking.de_To_Address_Street_2,
                'pu_Address_PostalCode': booking.de_To_Address_PostalCode,
                'pu_Address_Suburb': booking.de_To_Address_Suburb,
                'pu_Address_Country': booking.de_To_Address_Country,
                'pu_Contact_F_L_Name': booking.de_to_Contact_F_LName,
                'pu_Phone_Main': booking.de_to_Phone_Main,
                'pu_Email': booking.de_Email,
                'pu_Address_State': booking.de_To_Address_State,
                'deToCompanyName': booking.puCompany,
                'de_To_Address_Street_1': booking.pu_Address_Street_1,
                'de_To_Address_Street_2': booking.pu_Address_street_2,
                'de_To_Address_PostalCode': booking.pu_Address_PostalCode,
                'de_To_Address_Suburb': booking.pu_Address_Suburb,
                'de_To_Address_Country': booking.pu_Address_Country,
                'de_to_Contact_F_LName': booking.pu_Contact_F_L_Name,
                'de_to_Phone_Main': booking.pu_Phone_Main,
                'de_Email': booking.pu_Email,
                'de_To_Address_State': booking.pu_Address_State,
                'pk_booking_id': booking.pk_booking_id,
            }
        else:
            newBooking = {
                'b_bookingID_Visual': Bookings.get_max_b_bookingID_Visual() + 1,
                'fk_client_warehouse': booking.fk_client_warehouse_id,
                'b_client_warehouse_code': booking.b_client_warehouse_code,
                'b_clientPU_Warehouse': booking.b_clientPU_Warehouse,
                'b_client_name': booking.b_client_name,
                'puCompany': booking.puCompany,
                'pu_Address_Street_1': booking.pu_Address_Street_1,
                'pu_Address_street_2': booking.pu_Address_street_2,
                'pu_Address_PostalCode': booking.pu_Address_PostalCode,
                'pu_Address_Suburb': booking.pu_Address_Suburb,
                'pu_Address_Country': booking.pu_Address_Country,
                'pu_Contact_F_L_Name': booking.pu_Contact_F_L_Name,
                'pu_Phone_Main': booking.pu_Phone_Main,
                'pu_Email': booking.pu_Email,
                'pu_Address_State': booking.pu_Address_State,
                'deToCompanyName': booking.deToCompanyName,
                'de_To_Address_Street_1': booking.de_To_Address_Street_1,
                'de_To_Address_Street_2': booking.de_To_Address_Street_2,
                'de_To_Address_PostalCode': booking.de_To_Address_PostalCode,
                'de_To_Address_Suburb': booking.de_To_Address_Suburb,
                'de_To_Address_Country': booking.de_To_Address_Country,
                'de_to_Contact_F_LName': booking.de_to_Contact_F_LName,
                'de_to_Phone_Main': booking.de_to_Phone_Main,
                'de_Email': booking.de_Email,
                'de_To_Address_State': booking.de_To_Address_State,
                'pk_booking_id': booking.pk_booking_id,
            }

        if dup_line_and_linedetail == 'true':
            newBooking['pk_booking_id'] = str(uuid.uuid1())
            booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
            booking_line_details = Booking_lines_data.objects.filter(fk_booking_id=booking.pk_booking_id)
            for booking_line in booking_lines:
                booking_line.pk_lines_id = None
                booking_line.fk_booking_id = newBooking['pk_booking_id']
                booking_line.save()
            for booking_line_detail in booking_line_details:
                booking_line_detail.pk_id_lines_data = None
                booking_line_detail.fk_booking_id = newBooking['pk_booking_id']
                booking_line_detail.save()
        else:
            newBooking['pk_booking_id'] = str(uuid.uuid1())

        serializer = BookingSerializer(data=newBooking)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BookingLinesViewSet(viewsets.ViewSet):
    serializer_class = BookingLineSerializer

    @action(detail=False, methods=['get'])
    def get_booking_lines(self, request, format=None):
        pk_booking_id = request.GET['pk_booking_id']

        if pk_booking_id == 'undefined':
            booking_lines = Booking_lines.objects.all()
            return_data = []

            for booking_line in booking_lines:
                return_data.append({
                    'pk_lines_id': booking_line.pk_lines_id, 
                    'e_type_of_packaging': booking_line.e_type_of_packaging, 
                    'e_item': booking_line.e_item, 
                    'e_qty': booking_line.e_qty, 
                    'e_weightUOM': booking_line.e_weightUOM, 
                    'e_weightPerEach': booking_line.e_weightPerEach, 
                    'e_dimUOM': booking_line.e_dimUOM, 
                    'e_dimLength': booking_line.e_dimLength, 
                    'e_dimWidth': booking_line.e_dimWidth, 
                    'e_dimHeight': booking_line.e_dimHeight,
                    'e_Total_KG_weight': booking_line.e_Total_KG_weight,
                    'e_1_Total_dimCubicMeter': booking_line.e_1_Total_dimCubicMeter,
                })

            return JsonResponse({'booking_lines': return_data})
        else:
            booking_lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
            return_data = []

            for booking_line in booking_lines:
                return_data.append({
                    'pk_lines_id': booking_line.pk_lines_id, 
                    'e_type_of_packaging': booking_line.e_type_of_packaging, 
                    'e_item': booking_line.e_item, 
                    'e_qty': booking_line.e_qty, 
                    'e_weightUOM': booking_line.e_weightUOM, 
                    'e_weightPerEach': booking_line.e_weightPerEach, 
                    'e_dimUOM': booking_line.e_dimUOM, 
                    'e_dimLength': booking_line.e_dimLength, 
                    'e_dimWidth': booking_line.e_dimWidth, 
                    'e_dimHeight': booking_line.e_dimHeight,
                    'e_Total_KG_weight': booking_line.e_Total_KG_weight,
                    'e_1_Total_dimCubicMeter': booking_line.e_1_Total_dimCubicMeter,
                })

            return JsonResponse({'booking_lines': return_data})

    @action(detail=False, methods=['post'])
    def create_booking_line(self, request, format=None):
        booking_line = Booking_lines.objects.get(pk=request.data['pk_lines_id'])
        newbooking_line = {
            'fk_booking_id': booking_line.fk_booking_id,
            'e_type_of_packaging': booking_line.e_type_of_packaging, 
            'e_item': booking_line.e_item, 
            'e_qty': booking_line.e_qty, 
            'e_weightUOM': booking_line.e_weightUOM, 
            'e_weightPerEach': booking_line.e_weightPerEach, 
            'e_dimUOM': booking_line.e_dimUOM, 
            'e_dimLength': booking_line.e_dimLength, 
            'e_dimWidth': booking_line.e_dimWidth, 
            'e_dimHeight': booking_line.e_dimHeight,
            'e_Total_KG_weight': booking_line.e_Total_KG_weight,
            'e_1_Total_dimCubicMeter': booking_line.e_1_Total_dimCubicMeter,
        }
        serializer = BookingLineSerializer(data=newbooking_line)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def update_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)
        serializer = BookingLineSerializer(booking_line, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)

        try:
            booking_line.delete()
            return JsonResponse({'Deleted BookingLine': booking_line})
        except Exception as e:
            print('Exception: ', e)
            return JsonResponse({'error': 'Can not delete BookingLine'})

class BookingLineDetailsViewSet(viewsets.ViewSet):
    serializer_class = BookingLineDetailSerializer

    @action(detail=False, methods=['get'])
    def get_booking_line_details(self, request, format=None):
        pk_booking_id = request.GET['pk_booking_id']

        if pk_booking_id == 'undefined':
            booking_line_details = Booking_lines_data.objects.all()
            return_data = []

            for booking_line_detail in booking_line_details:
                return_data.append({
                    'pk_id_lines_data': booking_line_detail.pk_id_lines_data,
                    'modelNumber': booking_line_detail.modelNumber, 
                    'itemDescription': booking_line_detail.itemDescription, 
                    'quantity': booking_line_detail.quantity, 
                    'itemFaultDescription': booking_line_detail.itemFaultDescription, 
                    'insuranceValueEach': booking_line_detail.insuranceValueEach, 
                    'gap_ra': booking_line_detail.gap_ra, 
                    'clientRefNumber': booking_line_detail.clientRefNumber
                })

            return JsonResponse({'booking_line_details': return_data})
        else:
            booking_line_details = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
            return_data = []

            for booking_line_detail in booking_line_details:
                return_data.append({
                    'pk_id_lines_data': booking_line_detail.pk_id_lines_data,
                    'modelNumber': booking_line_detail.modelNumber, 
                    'itemDescription': booking_line_detail.itemDescription, 
                    'quantity': booking_line_detail.quantity, 
                    'itemFaultDescription': booking_line_detail.itemFaultDescription, 
                    'insuranceValueEach': booking_line_detail.insuranceValueEach, 
                    'gap_ra': booking_line_detail.gap_ra, 
                    'clientRefNumber': booking_line_detail.clientRefNumber
                })

            return JsonResponse({'booking_line_details': return_data})

    @action(detail=False, methods=['post'])
    def create_booking_line_detail(self, request, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=request.data['pk_id_lines_data'])
        newbooking_line_detail = {
            'fk_booking_id': booking_line_detail.fk_booking_id,
            'modelNumber': booking_line_detail.modelNumber, 
            'itemDescription': booking_line_detail.itemDescription, 
            'quantity': booking_line_detail.quantity, 
            'itemFaultDescription': booking_line_detail.itemFaultDescription, 
            'insuranceValueEach': booking_line_detail.insuranceValueEach, 
            'gap_ra': booking_line_detail.gap_ra, 
            'clientRefNumber': booking_line_detail.clientRefNumber,
        }
        serializer = BookingLineDetailSerializer(data=newbooking_line_detail)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def update_booking_line_detail(self, request, pk, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=pk)
        serializer = BookingLineDetailSerializer(booking_line_detail, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_booking_line_detail(self, request, pk, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=pk)

        try:
            booking_line_detail.delete()
            return JsonResponse({'Deleted BookingLineDetail ': booking_line_detail})
        except Exception as e:
            print('Exception: ', e)
            return JsonResponse({'error': 'Can not delete BookingLineDetail'})

class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'

        if user_type == 'DME':
            clientWarehouseObject_list = Client_warehouses.objects.all().exclude(pk_id_client_warehouses = 100)
            queryset = clientWarehouseObject_list
            return queryset
        else:
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
            client_employee_role = client_employee.get_role()

            if client_employee_role == 'company':
                clientWarehouseObject_list = Client_warehouses.objects.select_related().filter(fk_id_dme_client_id = int(client_employee.fk_id_dme_client_id)).exclude(pk_id_client_warehouses = 100)
                queryset = clientWarehouseObject_list
                return queryset
            elif client_employee_role == 'warehouse':
                employee_warehouse_id = client_employee.warehouse_id
                employee_warehouse = Client_warehouses.objects.get(pk_id_client_warehouses = employee_warehouse_id)
                queryset = [employee_warehouse]
                return queryset
            
class AttachmentsUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, filename, format=None):
        file_obj = request.FILES['file']
        user_id = request.user.id
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'

        if user_type == 'DME':
            dme_account_num = 'dme_user'
        else:
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
            dme_account_num = client_employee[0].fk_id_dme_client.dme_account_num
        upload_file_name = request.FILES['file'].name
        prepend_name = str(dme_account_num) + '_' + upload_file_name

        uploadResult = handle_uploaded_file_attachments(request, request.FILES['file'])

        html = prepend_name
        return Response(uploadResult)

class CommsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_comms(self, requst, pk=None):
        user_id = self.request.user.id
        booking_id = self.request.GET['bookingId']
        sort_field = self.request.query_params.get('sortField', None)
        column_filters = json.loads(self.request.query_params.get('columnFilters', None))

        print('@20 - booking_id: ', booking_id)
        print('@21 - sort_field: ', sort_field)
        print('@22 - column_filters: ', column_filters)

        booking = Bookings.objects.get(id=booking_id)
        comms = Dme_comm_and_task.objects.filter(fk_booking_id=booking.pk_booking_id)

        # Sort
        if sort_field is None:
            comms = comms.order_by('id')
        else:
            comms = comms.order_by(sort_field)

        # Column filter
        try:
            column_filter = column_filters['id']
            comms = comms.filter(id__icontains=column_filter)
        except KeyError:
            column_filter = ''

        return_datas = []
        if len(comms) == 0:
            return JsonResponse({'comms': []})
        else:
            for comm in comms:
                return_data = {
                    'id': comm.id,
                    'fk_booking_id': comm.fk_booking_id,
                    'priority_of_log': comm.priority_of_log,
                    'assigned_to': comm.assigned_to,
                    'query': comm.query,
                    'dme_com_title': comm.dme_com_title,
                    'closed': comm.closed,
                    'status_log_closed_time': comm.status_log_closed_time,
                    'dme_detail': comm.dme_detail,
                    'dme_notes_type': comm.dme_notes_type,
                    'dme_notes_external': comm.dme_notes_external,
                    'due_by_date': comm.due_by_date,
                    'due_by_time': comm.due_by_time,
                }
                return_datas.append(return_data)
            return JsonResponse({'comms': return_datas})

    @action(detail=True, methods=['put'])
    def update_comm(self, request, pk, format=None):
        dme_comm_and_task = Dme_comm_and_task.objects.get(pk=pk)
        serializer = CommSerializer(dme_comm_and_task, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_comm(self, request, pk=None):
        serializer = CommSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                new_note_data = {
                    'comm': serializer.data['id'],
                    'dme_notes': request.data['dme_detail'],
                    'dme_notes_type': request.data['dme_notes_type'],
                    'dme_notes_no': 1,
                    'username': 'Stephen',
                }
                note_serializer = NoteSerializer(data=new_note_data)
                
                try:
                    if note_serializer.is_valid():
                        note_serializer.save()
                    else:
                        return Response(note_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print('Exception: ', e)
                    return Response(note_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_notes(self, requst, pk=None):
        user_id = self.request.user.id
        comm_id = self.request.GET['commId']

        print('@20 - comm_id: ', comm_id)

        notes = Dme_comm_notes.objects.filter(comm_id=comm_id)

        return_datas = []
        if len(notes) == 0:
            return JsonResponse({'notes': []})
        else:
            for note in notes:
                return_data = {
                    'id': note.id,
                    'username': note.username,
                    'dme_notes': note.dme_notes,
                    'dme_notes_type': note.dme_notes_type,
                    'dme_notes_no': note.dme_notes_no,
                    'z_modifiedTimeStamp': note.z_modifiedTimeStamp,
                }
                return_datas.append(return_data)
            return JsonResponse({'notes': return_datas})

    @action(detail=True, methods=['put'])
    def update_note(self, request, pk, format=None):
        dme_comm_note = Dme_comm_notes.objects.get(pk=pk)
        serializer = NoteSerializer(dme_comm_note, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_note(self, request, pk=None):
        serializer = NoteSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def handle_uploaded_file_attachments(request, f):
    try:
        bookingId = request.POST.get("warehouse_id", "")

        if bookingId == 'undefined':
            return 'failed'
        now = datetime.now()
        now1 = now.strftime("%Y%m%d_%H%M%S")
        name, extension = os.path.splitext(f.name)
        fileName = '/var/www/html/dme_api/media/attachments/' + name + '_' + str(now1) + extension

        with open(fileName, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

        user_id = request.user.id
        client = DME_clients.objects.get(pk_id_dme_client=user_id)
        bookingObject = Bookings.objects.get(id=bookingId)
        saveData = Dme_attachments(fk_id_dme_client=client, fk_id_dme_booking=bookingObject, fileName=fileName, linkurl='22', upload_Date=now)
        saveData.save()
        return 'ok'
    except Exception as e:
        print('Exception: ', e)
        return 'failed'

    #Save history on database.

@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def getSuburbs(request):
    requestType = request.GET.get('type')
    return_data = []

    try:
        resultObjects = []
        if requestType == 'state':
            resultObjects = Utl_suburbs.objects.all()
            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {'value': resultObject.state.lower(), 'label': resultObject.state}
                    try:
                        if return_data.index(temp) is None:
                            return_data.append({'value': resultObject.state.lower(), 'label': resultObject.state})
                    except:
                        return_data.append({'value': resultObject.state.lower(), 'label': resultObject.state})
                else:
                    return_data.append({'value': resultObject.state.lower(), 'label': resultObject.state})
        elif requestType == 'postalcode':
            stateName = request.GET.get('name')
            resultObjects = Utl_suburbs.objects.select_related().filter(state = stateName)
            
            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {'value': resultObject.postal_code, 'label': resultObject.postal_code}
                    try:
                        if return_data.index(temp) is None:
                            return_data.append({'value': resultObject.postal_code, 'label': resultObject.postal_code})
                    except:
                        return_data.append({'value': resultObject.postal_code, 'label': resultObject.postal_code})
                else:
                    return_data.append({'value': resultObject.postal_code, 'label': resultObject.postal_code})
        elif requestType == 'suburb':
            postalCode = request.GET.get('name')
            resultObjects = Utl_suburbs.objects.select_related().filter(postal_code = postalCode)

            for resultObject in resultObjects:
                if len(return_data) > 0:
                    temp = {'value': resultObject.suburb, 'label': resultObject.suburb}
                    try:
                        if return_data.index(temp) is None:
                            return_data.append({'value': resultObject.suburb, 'label': resultObject.suburb})
                    except:
                        return_data.append({'value': resultObject.suburb, 'label': resultObject.suburb})
                else:
                    return_data.append({'value': resultObject.suburb, 'label': resultObject.suburb})
        return JsonResponse({'type': requestType,'suburbs': return_data})
    except Exception as e:
        return JsonResponse({'type': requestType,'suburbs': ''})

class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, filename, format=None):
        file_obj = request.FILES['file']
        user_id = request.user.id
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'

        if user_type == 'DME':
            dme_account_num = 'dme_user'
        else: 
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
            dme_account_num = client_employee[0].fk_id_dme_client.dme_account_num

        upload_file_name = request.FILES['file'].name
        prepend_name = str(dme_account_num) + '_' + upload_file_name

        save2Redis(prepend_name + "_l_000_client_acct_number", dme_account_num)
        # save2Redis(prepend_name + "_b_client_name", client_employee[0].fk_id_dme_client.dme_account_num)

        handle_uploaded_file(request, dme_account_num, request.FILES['file'])

        html = prepend_name
        return Response(prepend_name)

def handle_uploaded_file(requst, dme_account_num, f):
    # live code
    with open('/var/www/html/dme_api/media/onedrive/' + str(dme_account_num) + '_' + f.name, 'wb+') as destination:
    # local code(local url)
    # with open('/Users/admin/work/goldmine/xlsimport/upload/' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    clearFileCheckHistory(str(dme_account_num) + '_' + f.name)

def upload_status(request):
    result = getFileCheckHistory(request.GET.get('filename'))

    if result == 0:
        return JsonResponse({'status_code': 0})
    elif result == 'success':
        return JsonResponse({'status_code': 1})
    else:
        return JsonResponse({'status_code': 2, 'errors': result})

def download_pdf(request):
    bookingIds = request.GET['ids']
    bookingIds = bookingIds.split(',')
    file_paths = [];
    label_names = [];

    for id in bookingIds:
        booking = Bookings.objects.get(id=id)

        if booking.z_label_url is not None and len(booking.z_label_url) is not 0:
            file_paths.append('/var/www/html/dme_api/static/pdfs/' + booking.z_label_url) # Dev & Prod
            # file_paths.append('/Users/admin/work/goldmine/dme_api/static/pdfs/' + booking.z_label_url) # Local (Test Case)
            label_names.append(booking.z_label_url)
            booking.z_downloaded_shipping_label_timestamp = datetime.now()
            booking.save()

    zip_subdir = "labels"
    zip_filename = "%s.zip" % zip_subdir

    s = io.BytesIO()
    zf = zipfile.ZipFile(s, "w")

    for index, file_path in enumerate(file_paths):
        zip_path = os.path.join(zip_subdir, file_path)
        zf.write(file_path, 'labels/' + label_names[index])
    zf.close()

    response = HttpResponse(s.getvalue(), "application/x-zip-compressed")
    response['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
    return response

def download_pod(request):
    bookingIds = request.GET['ids']
    only_new = request.GET['onlyNew']
    bookingIds = bookingIds.split(',')
    file_paths = [];
    pod_and_pod_signed_names = [];

    if only_new == 'ALL':
        for id in bookingIds:
            booking = Bookings.objects.get(id=id)

            if booking.z_pod_url is not None and len(booking.z_pod_url) is not 0:
                file_paths.append('/var/www/html/dme_api/static/imgs/' + booking.z_pod_url) # Dev & Prod
                # file_paths.append('/Users/admin/work/goldmine/dme_api/static/imgs/' + booking.z_pod_url) # Local (Test Case)
                pod_and_pod_signed_names.append(booking.z_pod_url)
                booking.z_downloaded_pod_timestamp = timezone.now()
                booking.save()

            if booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) is not 0:
                file_paths.append('/var/www/html/dme_api/static/imgs/' + booking.z_pod_signed_url) # Dev & Prod
                # file_paths.append('/Users/admin/work/goldmine/dme_api/static/imgs/' + booking.z_pod_signed_url) # Local (Test Case)
                pod_and_pod_signed_names.append(booking.z_pod_signed_url)
                booking.z_downloaded_pod_timestamp = timezone.now()
                booking.save()
    elif only_new == 'NEW':
        for id in bookingIds:
            booking = Bookings.objects.get(id=id)

            if booking.z_downloaded_pod_timestamp is None:
                if booking.z_pod_url is not None and len(booking.z_pod_url) is not 0:
                    file_paths.append('/var/www/html/dme_api/static/imgs/' + booking.z_pod_url) # Dev & Prod
                    # file_paths.append('/Users/admin/work/goldmine/dme_api/static/imgs/' + booking.z_pod_url) # Local (Test Case)
                    pod_and_pod_signed_names.append(booking.z_pod_url)
                    booking.z_downloaded_pod_timestamp = timezone.now()
                    booking.save()

                if booking.z_pod_signed_url is not None and len(booking.z_pod_signed_url) is not 0:
                    file_paths.append('/var/www/html/dme_api/static/imgs/' + booking.z_pod_signed_url) # Dev & Prod
                    # file_paths.append('/Users/admin/work/goldmine/dme_api/static/imgs/' + booking.z_pod_signed_url) # Local (Test Case)
                    pod_and_pod_signed_names.append(booking.z_pod_signed_url)
                    booking.z_downloaded_pod_timestamp = timezone.now()
                    booking.save()

    zip_subdir = "pod_and_pod_signed"
    zip_filename = "%s.zip" % zip_subdir

    s = io.BytesIO()
    zf = zipfile.ZipFile(s, "w")

    for index, file_path in enumerate(file_paths):
        zip_path = os.path.join(zip_subdir, file_path)
        zf.write(file_path, 'pod_and_pod_signed/' + pod_and_pod_signed_names[index])
    zf.close()

    response = HttpResponse(s.getvalue(), "application/x-zip-compressed")
    response['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
    return response

@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def getAttachmentsHistory(request):
    bookingId = request.GET.get('id')
    return_data = []
    
    try:
        resultObjects = []
        resultObjects = Dme_attachments.objects.select_related().filter(fk_id_dme_booking = bookingId)
        for resultObject in resultObjects:
            print('@bookingID', resultObject.fk_id_dme_booking.id)
            return_data.append({
                'pk_id_attachment': resultObject.pk_id_attachment, 
                'fk_id_dme_client': resultObject.fk_id_dme_client.pk_id_dme_client, 
                'fk_id_dme_booking': resultObject.fk_id_dme_booking.id, 
                'fileName': resultObject.fileName, 
                'linkurl': resultObject.linkurl, 
                'upload_Date': resultObject.upload_Date, 
            })
        return JsonResponse({'history': return_data})
    except Exception as e:
        print('@Exception', e)
        return JsonResponse({'history': ''})
