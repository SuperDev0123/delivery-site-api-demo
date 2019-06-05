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
from ast import literal_eval
from pydash import _
import pytz
import os
import io
import json
import zipfile
import uuid
import time

from .serializers import *
from .models import *
from .utils import clearFileCheckHistory, getFileCheckHistory, save2Redis, generate_csv, build_xml, build_xls_and_send, send_email, make_3digit

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
            return JsonResponse({'username': request.user.username, 
                                'clientname': client.company_name,
                                'clientId': client.dme_account_num})

    @action(detail=False, methods=['get'])
    def get_clients(self, request, format=None):
        user = self.request.user

        # if user.username != 'dme':
        #     return JsonResponse(status=400, data={'error': 'Current user can not access to this api'})
        # else:
        dme_clients = DME_clients.objects.all()

        if len(dme_clients) is 0:
            return JsonResponse({'dme_clients': []})
        else:
            return_data = [{'pk_id_dme_client': 0, 'company_name': 'dme', 'dme_account_num': 'dme_account_num'}]
            for client in dme_clients:
                return_data.append({'pk_id_dme_client': client.pk_id_dme_client, 'company_name': client.company_name, 'dme_account_num': client.dme_account_num})

            return JsonResponse({'dme_clients': return_data})

    @action(detail=False, methods=['get'])
    def get_user_date_filter_field(self, request, pk=None):
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
        new_pod = self.request.query_params.get('newPod', None)
        new_label = self.request.query_params.get('newLabel', None)
        client_pk = self.request.query_params.get('clientPK', None)
        # item_count_per_page = self.request.query_params.get('itemCountPerPage', 10)
        
        # if user_type == 'CLIENT':
        #     print('@01 - Client filter: ', client.dme_account_num)
        # else:
        #     print('@01 - DME user')

        # if start_date == '*':
        #     print('@02 - Date filter: ', start_date)
        # else:    
        #     print('@02 - Date filter: ', start_date, end_date, first_date, last_date)

        # print('@03 - Warehouse ID filter: ', warehouse_id)
        # print('@04 - Sort field: ', sort_field)

        # if user_type == 'CLIENT':
        #     print('@05 - Company name: ', client.company_name)
        # else:
        #     print('@05 - Company name: DME')
        
        # print('@06 - Prefilter: ', prefilter)
        # print('@07 - Simple search keyword: ', simple_search_keyword)
        # print('@08 - New POD: ', new_pod)
        # print('@09 - Client PK: ', client_pk)

        # DME & Client filter
        if user_type == 'DME':
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == 'company':
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == 'warehouse':
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)

        # Client filter
        if client_pk is not '0':
            client = DME_clients.objects.get(pk_id_dme_client=int(client_pk))
            queryset = queryset.filter(kf_client_id=client.dme_account_num)

        if search_type == 'FILTER':
            # Date filter
            if user_type == 'DME':
                queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
            else:
                if client.company_name == 'Seaway' or client.company_name =='Seaway-Hanalt' or client.company_name == 'Tempo':
                    queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
                elif client.company_name == 'BioPak':
                    queryset = queryset.filter(puPickUpAvailFrom_Date__range=(first_date, last_date))
    
        # Warehouse filter
        if int(warehouse_id) is not 0:
            queryset = queryset.filter(fk_client_warehouse=int(warehouse_id))

        # Simple search & Column fitler
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
                Q(s_21_Actual_Delivery_TimeStamp__icontains=simple_search_keyword) |
                Q(b_client_sales_inv_num__icontains=simple_search_keyword) |
                Q(pu_Contact_F_L_Name__icontains=simple_search_keyword))
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

            try:
                column_filter = column_filters['b_client_sales_inv_num']
                queryset = queryset.filter(b_client_sales_inv_num__icontains=column_filter)
            except KeyError:
                column_filter = ''

        # New POD filter
        if new_pod == 'true':
            queryset = queryset.filter(z_downloaded_pod_timestamp__isnull=True) \
                                .exclude((Q(z_pod_url__isnull=True) | Q(z_pod_url__exact='')), \
                                (Q(z_pod_signed_url__isnull=True)| Q(z_pod_signed_url__exact='')))

        # New POD filter
        if new_label == 'true':
            queryset = queryset.filter(z_downloaded_shipping_label_timestamp__isnull=True) \
                                .exclude((Q(z_label_url__isnull=True) | Q(z_label_url__exact='')))

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
                'has_comms': booking.has_comms(),
                'b_client_sales_inv_num': booking.b_client_sales_inv_num,
                'z_lock_status': booking.z_lock_status,
                'business_group': booking.get_group_name(),
                'de_Deliver_By_Date': booking.de_Deliver_By_Date,
                'de_Deliver_From_Date': booking.de_Deliver_From_Date,
                'dme_delivery_status_category': booking.get_dme_delivery_status_category(),
                'dme_status_detail': booking.dme_status_detail,
                'dme_status_action': booking.dme_status_action,
                'vx_fp_del_eta_time': booking.vx_fp_del_eta_time,
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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put'])
    def change_bookings_status(self, request, format=None):
        status = request.data['status']
        booking_ids = request.data['bookingIds']

        try:
            for booking_id in booking_ids:
                booking = Bookings.objects.get(pk=booking_id)

                # Create new status_history
                dme_status_history = Dme_status_history(fk_booking_id=booking.pk_booking_id)
                dme_status_history.status_old = booking.b_status
                dme_status_history.notes = str(booking.b_status) + " ---> " + str(status)
                dme_status_history.status_last = status
                dme_status_history.event_time_stamp = datetime.now()
                dme_status_history.recipient_name = ''
                dme_status_history.status_update_via = ''
                dme_status_history.z_createdByAccount = request.user.username
                dme_status_history.save()

                # When new status is `Collected`
                if status == 'Collected':
                    booking_lines = Booking_lines.objects.filter(fk_booking_id = booking.pk_booking_id)
                    for booking_line in booking_lines:
                        booking_line.e_qty_collected = booking_line.e_qty - booking_line.e_qty_awaiting_inventory  
                        booking_line.save()

                booking.b_status = status
                booking.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            # print('Exception: ', e)
            return Response({'status': 'error'})

    @action(detail=False, methods=['get'])
    def generate_xls(self, request, format=None):
        user_id = int(self.request.user.id)
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'
            client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
            client_employee_role = client_employee.get_role()
            client = DME_clients.objects.select_related().filter(pk_id_dme_client = int(client_employee.fk_id_dme_client_id)).first()

        vx_freight_provider = self.request.query_params.get('vx_freight_provider', None)
        report_type = self.request.query_params.get('report_type', None)
        email_addr = self.request.query_params.get('emailAddr', None)
        show_field_name = self.request.query_params.get('showFieldName', None)

        if show_field_name == 'true':
            show_field_name = True
        else:
            show_field_name = False

        start_date = self.request.query_params.get('startDate', None)
        end_date = self.request.query_params.get('endDate', None)

        first_date = datetime.strptime(start_date, '%Y-%m-%d')
        last_date = (datetime.strptime(end_date, '%Y-%m-%d')+timedelta(days=1))
        
        # DME & Client filter
        if user_type == 'DME':
            queryset = Bookings.objects.all()
        else:
            if client_employee_role == 'company':
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)
            elif client_employee_role == 'warehouse':
                employee_warehouse_id = client_employee.warehouse_id
                queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)

        # Date filter
        if user_type == 'DME':
            queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
        else:
            if client.company_name == 'Seaway' or client.company_name =='Seaway-Hanalt' or client.company_name == 'Tempo':
                queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
            elif client.company_name == 'BioPak':
                queryset = queryset.filter(puPickUpAvailFrom_Date__range=(first_date, last_date))

        # Freight Provider filter
        if vx_freight_provider != 'All':
            queryset = queryset.filter(vx_freight_provider=vx_freight_provider)

        build_xls_and_send(queryset, email_addr, report_type, str(self.request.user), first_date, last_date, show_field_name)
        return JsonResponse({'status': 'started generate xml'})

    @action(detail=False, methods=['post'])
    def calc_collected(self, request, format=None):
        booking_ids = request.data["bookignIds"]
        type = request.data["type"]

        try:
            for id in booking_ids:
                booking = Bookings.objects.get(id=int(id))
                booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)

                for booking_line in booking_lines:
                    if type == 'Calc':
                        if not booking_line.e_qty:
                            booking_line.e_qty = 0
                        if not booking_line.e_qty_awaiting_inventory:
                            booking_line.e_qty_awaiting_inventory = 0

                        booking_line.e_qty_collected = int(booking_line.e_qty) - int(booking_line.e_qty_awaiting_inventory)
                        booking_line.save()
                    elif type == 'Clear':
                        booking_line.e_qty_collected = 0
                        booking_line.save()
            return JsonResponse({'success': 'All bookings e_qty_collected has been calculated'})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({'error': 'Got error, please contact support center'})

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
                        'z_lock_status': booking.z_lock_status,
                        'tally_delivered': booking.tally_delivered,
                        'dme_status_history_notes': booking.dme_status_history_notes,
                        'dme_status_detail': booking.dme_status_detail,
                        'dme_status_action': booking.dme_status_action,
                        'dme_status_linked_reference_from_fp': booking.dme_status_linked_reference_from_fp,
                        'pu_PickUp_Avail_From_Date_DME': booking.pu_PickUp_Avail_From_Date_DME,
                        'pu_PickUp_Avail_Time_Hours': booking.pu_PickUp_Avail_Time_Hours,
                        'pu_PickUp_Avail_Time_Minutes': booking.pu_PickUp_Avail_Time_Minutes,
                        'pu_PickUp_By_Date_DME': booking.pu_PickUp_By_Date_DME,
                        'pu_PickUp_By_Time_Hours_DME': booking.pu_PickUp_By_Time_Hours_DME,
                        'pu_PickUp_By_Time_Minutes_DME': booking.pu_PickUp_By_Time_Minutes_DME,
                        'de_Deliver_From_Date': booking.de_Deliver_From_Date,
                        'de_Deliver_From_Hours': booking.de_Deliver_From_Hours,
                        'de_Deliver_From_Minutes': booking.de_Deliver_From_Minutes,
                        'de_Deliver_By_Date': booking.de_Deliver_By_Date,
                        'de_Deliver_By_Hours': booking.de_Deliver_By_Hours,
                        'de_Deliver_By_Minutes': booking.de_Deliver_By_Minutes,
                        'client_item_references': booking.get_client_item_references(),
                    }
                    return JsonResponse({'booking': return_data, 'nextid': nextBookingId, 'previd': prevBookingId})
            else:
                return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})
        except Bookings.DoesNotExist:
            return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})

    @action(detail=False, methods=['get'])
    def get_latest_booking(self, request, format=None):
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
            
            booking = queryset.last()

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
                        'z_lock_status': booking.z_lock_status,
                        'tally_delivered': booking.tally_delivered,
                        'dme_status_history_notes': booking.dme_status_history_notes,
                        'dme_status_detail': booking.dme_status_detail,
                        'dme_status_action': booking.dme_status_action,
                        'dme_status_linked_reference_from_fp': booking.dme_status_linked_reference_from_fp,
                        'pu_PickUp_Avail_From_Date_DME': booking.pu_PickUp_Avail_From_Date_DME,
                        'pu_PickUp_Avail_Time_Hours': booking.pu_PickUp_Avail_Time_Hours,
                        'pu_PickUp_Avail_Time_Minutes': booking.pu_PickUp_Avail_Time_Minutes,
                        'pu_PickUp_By_Date_DME': booking.pu_PickUp_By_Date_DME,
                        'pu_PickUp_By_Time_Hours_DME': booking.pu_PickUp_By_Time_Hours_DME,
                        'pu_PickUp_By_Time_Minutes_DME': booking.pu_PickUp_By_Time_Minutes_DME,
                        'de_Deliver_From_Date': booking.de_Deliver_From_Date,
                        'de_Deliver_From_Hours': booking.de_Deliver_From_Hours,
                        'de_Deliver_From_Minutes': booking.de_Deliver_From_Minutes,
                        'de_Deliver_By_Date': booking.de_Deliver_By_Date,
                        'de_Deliver_By_Hours': booking.de_Deliver_By_Hours,
                        'de_Deliver_By_Minutes': booking.de_Deliver_By_Minutes,
                        'client_item_references': booking.get_client_item_references(),
                    }
                    return JsonResponse({'booking': return_data, 'nextid': nextBookingId, 'previd': prevBookingId})
            else:
                return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})
        except Bookings.DoesNotExist:
            return JsonResponse({'booking': {}, 'nextid': 0, 'previd': 0})

    @action(detail=False, methods=['post'])
    def create_booking(self, request, format=None):
        bookingData = request.data
        bookingData['b_bookingID_Visual'] = Bookings.get_max_b_bookingID_Visual() + 1
        bookingData['pk_booking_id'] = str(uuid.uuid1()) + '_' + str(time.time())

        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.data['client_item_references']
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
                'z_lock_status': booking.z_lock_status,
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
                'z_lock_status': booking.z_lock_status,
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
        return_data = []

        if pk_booking_id == 'undefined':
            booking_lines = Booking_lines.objects.all()
        else:
            booking_lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)

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
                'total_2_cubic_mass_factor_calc': booking_line.total_2_cubic_mass_factor_calc,
                'e_qty_awaiting_inventory': booking_line.e_qty_awaiting_inventory,
                'e_qty_collected': booking_line.e_qty_collected,
                'e_qty_scanned_depot': booking_line.e_qty_scanned_depot,
                'e_qty_delivered': booking_line.e_qty_delivered,
                'e_qty_adjusted_delivered': booking_line.e_qty_adjusted_delivered,
                'e_qty_damaged': booking_line.e_qty_damaged,
                'e_qty_returned': booking_line.e_qty_returned,
                'e_qty_shortages': booking_line.e_qty_shortages,
                'e_qty_scanned_fp': booking_line.e_qty_scanned_fp,
                'is_scanned': booking_line.get_is_scanned(),
            })

        return JsonResponse({'booking_lines': return_data})

    @action(detail=False, methods=['post'])
    def create_booking_line(self, request, format=None):
        serializer = BookingLineSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def duplicate_booking_line(self, request, format=None):
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
            'total_2_cubic_mass_factor_calc': booking_line.total_2_cubic_mass_factor_calc,
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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_booking_line(self, request, pk, format=None):
        booking_line = Booking_lines.objects.get(pk=pk)

        try:
            booking_line.delete()
            return JsonResponse({'Deleted BookingLine': booking_line})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({'error': 'Can not delete BookingLine'})

    @action(detail=False, methods=['post'])
    def calc_collected(self, request, format=None):
        ids = request.data["ids"]
        type = request.data["type"]

        try:
            for id in ids:
                booking_line = Booking_lines.objects.get(pk_lines_id=id)

                if type == 'Calc':
                    if not booking_line.e_qty:
                        booking_line.e_qty = 0
                    if not booking_line.e_qty_awaiting_inventory:
                        booking_line.e_qty_awaiting_inventory = 0

                    booking_line.e_qty_collected = int(booking_line.e_qty) - int(booking_line.e_qty_awaiting_inventory)
                    booking_line.save()
                elif type == 'Clear':
                    booking_line.e_qty_collected = 0
                    booking_line.save()
            return JsonResponse({'success': 'All bookings e_qty_collected has been calculated'})
        except Exception as e:
            print('Exception: ', e)
            return JsonResponse({'error': 'Got error, please contact support center'})

class BookingLineDetailsViewSet(viewsets.ViewSet):
    serializer_class = BookingLineDetailSerializer

    @action(detail=False, methods=['get'])
    def get_booking_line_details(self, request, format=None):
        pk_booking_id = request.GET['pk_booking_id']
        return_data = []

        if pk_booking_id == 'undefined':
            booking_line_details = Booking_lines_data.objects.all()
        else:
            booking_line_details = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)

        for booking_line_detail in booking_line_details:
            return_data.append({
                'pk_id_lines_data': booking_line_detail.pk_id_lines_data,
                'modelNumber': booking_line_detail.modelNumber, 
                'itemDescription': booking_line_detail.itemDescription, 
                'quantity': booking_line_detail.quantity, 
                'itemFaultDescription': booking_line_detail.itemFaultDescription, 
                'insuranceValueEach': booking_line_detail.insuranceValueEach, 
                'gap_ra': booking_line_detail.gap_ra, 
                'clientRefNumber': booking_line_detail.clientRefNumber,
                'fk_id_booking_lines': booking_line_detail.fk_id_booking_lines,
            })

        return JsonResponse({'booking_line_details': return_data})

    @action(detail=False, methods=['post'])
    def create_booking_line_detail(self, request, format=None):
        serializer = BookingLineDetailSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def duplicate_booking_line_detail(self, request, format=None):
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
            'fk_id_booking_lines': booking_line_detail.fk_id_booking_lines,
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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_booking_line_detail(self, request, pk, format=None):
        booking_line_detail = Booking_lines_data.objects.get(pk=pk)

        try:
            booking_line_detail.delete()
            return JsonResponse({'Deleted BookingLineDetail ': booking_line_detail})
        except Exception as e:
            # print('Exception: ', e)
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
    def get_comms(self, request, pk=None):
        def convert_date(date):
            if not date:
                date = datetime(2100, 1, 1).date()

            return date

        def reverse_date(object):
            if object['due_by_date'] == datetime(2100, 1, 1).date():
                object['due_by_date'] = None

            return object

        user_id = self.request.user.id
        booking_id = self.request.GET['bookingId']
        sort_field = self.request.query_params.get('sortField', None)
        sort_type = self.request.query_params.get('sortType', None)
        column_filters = json.loads(self.request.query_params.get('columnFilters', None))
        simple_search_keyword = self.request.query_params.get('simpleSearchKeyword', None) 
        sort_by_date = self.request.query_params.get('sortByDate', None) 
        active_tab_ind = int(self.request.query_params.get('activeTabInd', None))

        if not sort_field:
            sort_by_date = 'true'

        if booking_id == '':
            user_id = int(self.request.user.id)
            dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

            if dme_employee is not None:
                user_type = 'DME'
            else:
                user_type = 'CLIENT'
                client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
                client_employee_role = client_employee.get_role()
                client = DME_clients.objects.select_related().filter(pk_id_dme_client = int(client_employee.fk_id_dme_client_id)).first()

            # DME & Client filter
            if user_type == 'DME':
                bookings = Bookings.objects.all()
            else:
                if client_employee_role == 'company':
                    bookings = Bookings.objects.filter(kf_client_id=client.dme_account_num)
                elif client_employee_role == 'warehouse':
                    employee_warehouse_id = client_employee.warehouse_id
                    bookings = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)

            # Sort Comms
            if sort_type == 'bookings':
                if sort_field is None:
                    bookings = bookings.order_by('-id')
                else:
                    bookings = bookings.order_by(sort_field)

            # Simple search & Column fitler
            is_booking_filtered = True
            if len(simple_search_keyword) > 0:
                filtered_bookings = bookings.filter(
                    Q(b_bookingID_Visual__icontains=simple_search_keyword) | 
                    Q(b_status__icontains=simple_search_keyword) | 
                    Q(vx_freight_provider__icontains=simple_search_keyword) | 
                    Q(puCompany__icontains=simple_search_keyword) |
                    Q(deToCompanyName__icontains=simple_search_keyword) |
                    Q(v_FPBookingNumber__icontains=simple_search_keyword))

                if len(filtered_bookings) == 0:
                    is_booking_filtered = False
                else:
                    is_booking_filtered = True
                    bookings = filtered_bookings
            else:
                # Column Bookings filter
                try:
                    column_filter = column_filters['b_bookingID_Visual']
                    bookings = bookings.filter(b_bookingID_Visual__icontains=column_filter)
                except KeyError:
                    column_filter = ''
                try:
                    column_filter = column_filters['b_status']
                    bookings = bookings.filter(b_status__icontains=column_filter)
                except KeyError:
                    column_filter = ''
                try:
                    column_filter = column_filters['vx_freight_provider']
                    bookings = bookings.filter(vx_freight_provider__icontains=column_filter)
                except KeyError:
                    column_filter = ''
                try:
                    column_filter = column_filters['puCompany']
                    bookings = bookings.filter(puCompany__icontains=column_filter)
                except KeyError:
                    column_filter = ''
                try:
                    column_filter = column_filters['deToCompanyName']
                    bookings = bookings.filter(deToCompanyName__icontains=column_filter)
                except KeyError:
                    column_filter = ''
                try:
                    column_filter = column_filters['v_FPBookingNumber']
                    bookings = bookings.filter(v_FPBookingNumber__icontains=column_filter)
                except KeyError:
                    column_filter = ''

            return_datas = []
            opened_comms_cnt = 0
            closed_comms_cnt = 0
            for booking in bookings:
                comms = Dme_comm_and_task.objects.filter(fk_booking_id=booking.pk_booking_id)

                # Sort Comms
                if sort_type == 'comms':
                    if sort_field is None:
                        comms = comms.order_by('-id')
                    else:
                        comms = comms.order_by(sort_field)

                # Simple search & Column fitler
                if len(simple_search_keyword) > 0:
                    new_comms = comms.filter(
                        Q(id__icontains=simple_search_keyword) | 
                        Q(priority_of_log__icontains=simple_search_keyword) | 
                        Q(assigned_to__icontains=simple_search_keyword) | 
                        Q(dme_notes_type__icontains=simple_search_keyword) |
                        Q(query__icontains=simple_search_keyword) |
                        Q(dme_action__icontains=simple_search_keyword) | 
                        Q(status_log_closed_time__icontains=simple_search_keyword) | 
                        Q(dme_detail__icontains=simple_search_keyword) |
                        Q(dme_notes_external__icontains=simple_search_keyword) |
                        Q(due_by_date__icontains=simple_search_keyword) |
                        Q(due_by_time__icontains=simple_search_keyword))

                    if len(new_comms) == 0 and is_booking_filtered == False:
                        comms = []
                    elif len(new_comms) > 0:
                        comms = new_comms

                else:
                    # Column Comms filter
                    try:
                        column_filter = column_filters['id']
                        comms = comms.filter(id__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['priority_of_log']
                        comms = comms.filter(priority_of_log__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['assigned_to']
                        comms = comms.filter(assigned_to__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['dme_notes_type']
                        comms = comms.filter(dme_notes_type__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['query']
                        comms = comms.filter(query__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['dme_action']
                        comms = comms.filter(dme_action__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['status_log_closed_time']
                        comms = comms.filter(status_log_closed_time__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['dme_detail']
                        comms = comms.filter(dme_detail__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['dme_notes_external']
                        comms = comms.filter(dme_notes_external__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['due_by_date']
                        comms = comms.filter(due_by_date__icontains=column_filter)
                    except KeyError:
                        column_filter = ''
                    try:
                        column_filter = column_filters['due_by_time']
                        comms = comms.filter(due_by_time__icontains=column_filter)
                    except KeyError:
                        column_filter = ''

                opened_comms = comms.filter(closed=False)
                closed_comms = comms.filter(closed=True)
                opened_comms_cnt = opened_comms_cnt + len(opened_comms)
                closed_comms_cnt = closed_comms_cnt + len(closed_comms)

                if active_tab_ind == 1 and len(comms) > 0:
                    comms = comms.filter(closed=False)
                elif active_tab_ind == 2 and len(comms) > 0:
                    comms = comms.filter(closed=True)

                for index, comm in enumerate(comms):
                    return_data = {
                        'b_bookingID_Visual': booking.b_bookingID_Visual,
                        'b_status': booking.b_status,
                        'vx_freight_provider': booking.vx_freight_provider,
                        'puCompany': booking.puCompany,
                        'deToCompanyName': booking.deToCompanyName,
                        'v_FPBookingNumber': booking.v_FPBookingNumber,
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
                        'due_by_datetime': str(comm.due_by_date) + ' ' + str(comm.due_by_time),
                        'due_by_date': convert_date(comm.due_by_date),
                        'due_by_time': comm.due_by_time,
                        'dme_action': comm.dme_action,
                        'z_createdTimeStamp': comm.z_createdTimeStamp,
                    }
                    return_datas.append(return_data)

            if sort_by_date == 'true':
                return_datas = _.sort_by(return_datas, 'due_by_date', reverse=True)

            return_datas = _.chain(return_datas).map(lambda x: reverse_date(x)).value()

            return JsonResponse({'comms': return_datas, 'cnts': { 'opened_cnt': opened_comms_cnt, 'closed_cnt': closed_comms_cnt, 'all_cnt': len(return_datas), 'selected_cnt': -1}})
        else:
            booking = Bookings.objects.get(id=booking_id)
            comms = Dme_comm_and_task.objects.filter(fk_booking_id=booking.pk_booking_id)

            # Sort
            if sort_field is None:
                comms = comms.order_by('-id')
            else:
                comms = comms.order_by(sort_field)

            # Column filter
            try:
                column_filter = column_filters['id']
                comms = comms.filter(id__icontains=column_filter)
            except KeyError:
                column_filter = ''

            opened_comms = comms.filter(closed=False)
            closed_comms = comms.filter(closed=True)

            if active_tab_ind == 1 and len(comms) > 0:
                comms = comms.filter(closed=False)
            elif active_tab_ind == 2 and len(comms) > 0:
                comms = comms.filter(closed=True)

            # Get All Comms Count #
            all_comms_cnt = 0
            user_id = int(self.request.user.id)
            dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()
            if dme_employee is not None:
                user_type = 'DME'
            else:
                user_type = 'CLIENT'
                client_employee = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
                client_employee_role = client_employee.get_role()
                client = DME_clients.objects.select_related().filter(pk_id_dme_client = int(client_employee.fk_id_dme_client_id)).first()

            # DME & Client filter
            if user_type == 'DME':
                bookings = Bookings.objects.all()
            else:
                if client_employee_role == 'company':
                    bookings = Bookings.objects.filter(kf_client_id=client.dme_account_num)
                elif client_employee_role == 'warehouse':
                    employee_warehouse_id = client_employee.warehouse_id
                    bookings = Bookings.objects.filter(kf_client_id=client.dme_account_num, fk_client_warehouse_id=employee_warehouse_id)

            for each_booking in bookings:
                all_comms = Dme_comm_and_task.objects.filter(fk_booking_id=each_booking.pk_booking_id)
                all_comms_cnt = all_comms_cnt + len(all_comms)
            #########################


            return_datas = []
            if len(comms) == 0:
                return JsonResponse({'comms': [], 'cnts': {'opened_cnt': 0, 'closed_cnt': 0, 'selected_cnt': 0, 'all_cnt': len(all_comms)}})
            else:
                for index, comm in enumerate(comms):
                    return_data = {
                        'index': index + 1,
                        'b_bookingID_Visual': booking.b_bookingID_Visual,
                        'b_status': booking.b_status,
                        'vx_freight_provider': booking.vx_freight_provider,
                        'puCompany': booking.puCompany,
                        'deToCompanyName': booking.deToCompanyName,
                        'v_FPBookingNumber': booking.v_FPBookingNumber,
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
                        'due_by_datetime': str(comm.due_by_date) + ' ' + str(comm.due_by_time),
                        'due_by_date': convert_date(comm.due_by_date),
                        'due_by_time': comm.due_by_time,
                        'dme_action': comm.dme_action,
                        'z_createdTimeStamp': comm.z_createdTimeStamp,
                    }
                    return_datas.append(return_data)

                if sort_by_date == 'true':
                    return_datas = _.sort_by(return_datas, 'due_by_date', reverse=True)

                return_datas = _.chain(return_datas).map(lambda x: reverse_date(x)).value()

                return JsonResponse({'comms': return_datas, 'cnts': {'opened_cnt': len(opened_comms), 'closed_cnt': len(closed_comms), 'selected_cnt': len(comms), 'all_cnt': all_comms_cnt}})

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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_comm(self, request, pk=None):
        serializer = CommSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                new_note_data = {
                    'comm': serializer.data['id'],
                    'dme_notes': request.data['dme_notes'],
                    'dme_notes_type': request.data['notes_type'],
                    'note_date_updated': request.data['due_by_date'],
                    'note_time_updated': request.data['due_by_time'],
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
                    # print('Exception 01: ', e)
                    return Response(note_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception 02: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def get_available_creators(self, request, pk=None):
        users = User.objects.all()
        creators = []

        for user in users:
            user_permission = UserPermissions.objects.filter(user_id=user.id).first()
            if user_permission and user_permission.can_create_comm:
                creators.append({'username': user.username, 'first_name': user.first_name, 'last_name': user.last_name})
        
        return JsonResponse({'creators': creators})

    @action(detail=True, methods=['delete'])
    def delete_comm(self, request, pk, format=None):
        comm = Dme_comm_and_task.objects.get(pk=pk)

        try:
            notes = Dme_comm_notes.objects.filter(comm=comm)

            for note in notes:
                note.delete()

            comm.delete()
            return JsonResponse({'status': 'Successfully deleted a comm'})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({'error': 'Can not delete Comm'})

class NotesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_notes(self, request, pk=None):
        user_id = self.request.user.id
        comm_id = self.request.GET['commId']

        # print('@20 - comm_id: ', comm_id)

        notes = Dme_comm_notes.objects.filter(comm_id=comm_id).order_by('-id')

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
                    'note_date_created': note.note_date_created,
                    'note_date_updated': note.note_date_updated,
                    'note_time_created': note.note_time_created,
                    'note_time_updated': note.note_time_updated,
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
            # print('Exception: ', e)
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
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_note(self, request, pk, format=None):
        note = Dme_comm_notes.objects.get(pk=pk)

        try:
            note.delete()
            return JsonResponse({'status': 'Successfully deleted a note'})
        except Exception as e:
            # print('Exception: ', e)
            return JsonResponse({'error': 'Can not delete Note'})

class PackageTypesViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_packagetypes(self, request, pk=None):
        packageTypes = Dme_package_types.objects.all()

        return_datas = []
        if len(packageTypes) == 0:
            return JsonResponse({'packageTypes': []})
        else:
            for packageType in packageTypes:
                return_data = {
                    'id': packageType.id,
                    'dmePackageTypeCode': packageType.dmePackageTypeCode,
                    'dmePackageCategory': packageType.dmePackageCategory,
                    'dmePackageTypeDesc': packageType.dmePackageTypeDesc,
                }
                return_datas.append(return_data)
            return JsonResponse({'packageTypes': return_datas})

class BookingStatusViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_all_booking_status(self, request, pk=None):
        user_id = request.user.id
        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'

        if user_type == 'DME':
            all_booking_status = Utl_dme_status.objects.all().order_by('sort_order')
        else:
            all_booking_status = Utl_dme_status.objects.filter(z_show_client_option=1).order_by('sort_order')

        return_datas = []
        if len(all_booking_status) == 0:
            return JsonResponse({'all_booking_status': []})
        else:
            for booking_status in all_booking_status:
                return_data = {
                    'id': booking_status.id,
                    'dme_delivery_status': booking_status.dme_delivery_status,
                }
                return_datas.append(return_data)
            return JsonResponse({'all_booking_status': return_datas})

class StatusHistoryViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_all(self, request, pk=None):
        pk_booking_id = self.request.GET.get('pk_booking_id')
        return_data = []

        try:
            resultObjects = []
            resultObjects = Dme_status_history.objects.select_related().filter(fk_booking_id=pk_booking_id).order_by('-id')
            for resultObject in resultObjects:
                return_data.append({
                    'id': resultObject.id,
                    'notes': resultObject.notes,
                    'status_last': resultObject.status_last,
                    'event_time_stamp': resultObject.event_time_stamp,
                    'dme_notes': resultObject.dme_notes,
                    'z_createdTimeStamp': resultObject.z_createdTimeStamp,
                    'dme_status_detail': resultObject.dme_status_detail,
                    'dme_status_action': resultObject.dme_status_action,
                    'dme_status_linked_reference_from_fp': resultObject.dme_status_linked_reference_from_fp,
                })
            return JsonResponse({'history': return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'history': ''})

    @action(detail=False, methods=['post'])
    def save_status_history(self, request, pk=None):
        serializer = StatusHistorySerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def update_status_history(self, request, pk, format=None):
        status_history = Dme_status_history.objects.get(pk=pk)
        serializer = StatusHistorySerializer(status_history, data=request.data)

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # print('Exception: ', e)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FPViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_all(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Fp_freight_providers.objects.all()
            for resultObject in resultObjects:
                if not resultObject.fp_inactive_date:
                    return_data.append({
                        'id': resultObject.id,
                        'fp_company_name': resultObject.fp_company_name,
                    })
            return JsonResponse({'results': return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'results': ''})

class StatusViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_status_actions(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_dme_status_actions.objects.all()
            for resultObject in resultObjects:
                return_data.append({
                    'id': resultObject.id,
                    'dme_status_action': resultObject.dme_status_action,
                })
            return JsonResponse({'results': return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'results': ''})

    @action(detail=False, methods=['post'])
    def create_status_action(self, request, pk=None):
        try:
            utl_dme_status_action = Utl_dme_status_actions(dme_status_action=request.data['newStatusAction'])
            utl_dme_status_action.save()
            return JsonResponse({'success': 'Created new status action'});
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'error': 'Can not create new status action'});

    @action(detail=False, methods=['get'])
    def get_status_details(self, request, pk=None):
        return_data = []

        try:
            resultObjects = []
            resultObjects = Utl_dme_status_details.objects.all()
            for resultObject in resultObjects:
                return_data.append({
                    'id': resultObject.id,
                    'dme_status_detail': resultObject.dme_status_detail,
                })
            return JsonResponse({'results': return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'results': ''})

    @action(detail=False, methods=['post'])
    def create_status_detail(self, request, pk=None):
        try:
            utl_dme_status_action = Utl_dme_status_details(dme_status_detail=request.data['newStatusDetail'])
            utl_dme_status_action.save()
            return JsonResponse({'success': 'Created new status detail'});
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'error': 'Can not create new status action'});

class ApiBCLViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def get_api_bcls(self, request, pk=None):
        booking_id = request.GET['bookingId']
        booking = Bookings.objects.get(id=int(booking_id))
        return_data = []

        try:
            resultObjects = []
            resultObjects = Api_booking_confirmation_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
            for resultObject in resultObjects:
                return_data.append({
                    'id': resultObject.id,
                    'fk_booking_id': resultObject.fk_booking_id,
                    'fk_booking_line_id': resultObject.fk_booking_line_id,
                    'label_code': resultObject.label_code,
                    'client_item_reference': resultObject.client_item_reference,
                    'fp_event_date': resultObject.fp_event_date,
                    'fp_event_time': resultObject.fp_event_time,
                })
            return JsonResponse({'results': return_data})
        except Exception as e:
            # print('@Exception', e)
            return JsonResponse({'results': ''})

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
        # print('Exception: ', e)
        return 'failed'

    #Save history on database.

class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, filename, format=None):
        file_obj = request.FILES['file']
        user_id = request.user.id
        username = request.user.username

        dme_employee = DME_employees.objects.select_related().filter(fk_id_user = user_id).first()

        if dme_employee is not None:
            user_type = 'DME'
        else:
            user_type = 'CLIENT'

        if user_type == 'DME':
            uploader = request.POST['uploader']
            dme_account_num = DME_clients.objects.get(company_name=uploader).dme_account_num
        else:
            client_employee = Client_employees.objects.get(fk_id_user=int(user_id))
            dme_account_num = client_employee.fk_id_dme_client.dme_account_num

        upload_file_name = request.FILES['file'].name
        prepend_name = str(dme_account_num) + '_' + upload_file_name

        save2Redis(prepend_name + "_l_000_client_acct_number", dme_account_num)
        # save2Redis(prepend_name + "_b_client_name", client_employee[0].fk_id_dme_client.dme_account_num)

        handle_uploaded_file(request, dme_account_num, request.FILES['file'])

        html = prepend_name
        return Response(prepend_name)

def handle_uploaded_file(request, dme_account_num, f):
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

@api_view(['POST'])
@permission_classes((AllowAny,))
def download_pdf(request):
    body = literal_eval(request.body.decode('utf8'))
    bookingIds = body["ids"]
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

@api_view(['POST'])
@permission_classes((AllowAny,))
def download_pod(request):
    body = literal_eval(request.body.decode('utf8'))
    bookingIds = body["ids"] 
    only_new = body["onlyNew"]
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

@api_view(['POST'])
@permission_classes((AllowAny,))
def download_csv(request):
    body = literal_eval(request.body.decode('utf8'))
    booking_ids = body["bookingIds"]
    file_paths = [];
    label_names = [];

    csv_name = generate_csv(booking_ids)

    for booking_id in booking_ids:
        booking = Bookings.objects.get(id=booking_id)

        ############################################################################################
        # This is a comment this is what I did and why to make this happen 05/09/2019 pete walbolt #
        ############################################################################################
        booking.b_dateBookedDate = datetime.now()
        booking.b_status = 'Booked CSV'
        booking.v_FPBookingNumber = 'DME' + str(booking.b_bookingID_Visual)
        booking.save()

        booking_lines = Booking_lines.objects.filter(fk_booking_id=booking.pk_booking_id)
        index = 1

        for booking_line in booking_lines:
            for i in range(int(booking_line.e_qty)):
                api_booking_confirmation_line = Api_booking_confirmation_lines(
                    fk_booking_id = booking.pk_booking_id, 
                    fk_booking_line_id = booking_line.pk_lines_id, 
                    api_item_id = str('COPDME') + str(booking.b_bookingID_Visual) + make_3digit(index),
                    service_provider = booking.vx_freight_provider,
                    label_code = str('COPDME') + str(booking.b_bookingID_Visual) + make_3digit(index),
                    client_item_reference = booking_line.client_item_reference
                )
                api_booking_confirmation_line.save()
                index = index + 1

    file_path = '/home/cope_au/dme_sftp/cope_au/pickup_ext/' + csv_name # Dev & Prod
    # file_path = '/Users/admin/work/goldmine/dme_api/static/csvs/' + csv_name # Local (Test Case)

    if os.path.exists(file_path):
        return JsonResponse({'filename': csv_name, 'status': 'Created CSV'})
        # with open(file_path, 'rb') as fh:
        #     response = HttpResponse(fh.read(), content_type="text/csv")
        #     # response['Content-Disposition'] = 'inline; filename=' + csv_name
        #     response['Content-Disposition'] = 'attachment; filename= "%s"' % csv_name
        #     return response

@api_view(['POST'])
@permission_classes((AllowAny,))
def generate_xml(request):
    body = literal_eval(request.body.decode('utf8'))
    booking_ids = body["bookingIds"]
    vx_freight_provider = body["vx_freight_provider"]

    try:
        booked_list = build_xml(booking_ids, vx_freight_provider)

        if len(booked_list) == 0:
            return JsonResponse({'success': 'success'})
        else:
            return JsonResponse({'error': 'Found set has booked bookings', 'booked_list': booked_list})
    except Exception as e:
        # print('generate_xml error: ', e)
        return JsonResponse({'error': 'error'})

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
            # print('@bookingID', resultObject.fk_id_dme_booking.id)
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
        # print('@Exception', e)
        return JsonResponse({'history': ''})

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
