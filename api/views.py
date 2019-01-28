from django.shortcuts import render
from rest_framework import views, status
from django.core import serializers
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework import authentication, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, action
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse
from django.http import QueryDict
from django.db.models import Q
from wsgiref.util import FileWrapper
from datetime import datetime, date, timedelta
import json
from time import gmtime, strftime
from .serializers import *
from .models import *
from .utils import clearFileCheckHistory, getFileCheckHistory, save2Redis

class UserViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def username(self, request, format=None):
        user_id = self.request.user.id
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
        clientObject = DME_clients.objects.get(pk_id_dme_client=clientEmployeObject.fk_id_dme_client_id)
        return JsonResponse({'username': request.user.username, 'clientname': clientObject.company_name})

    @action(detail=False, methods=['get'])
    def get_user_date_filter_field(self, requst, pk=None):
        user_id = self.request.user.id
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = user_id).first()
        clientObject = DME_clients.objects.get(pk_id_dme_client=clientEmployeObject.fk_id_dme_client_id)
        return JsonResponse({'user_date_filter_field': clientObject.client_filter_date_field})

class BookingLinesView(APIView):
    def get(self, request, format=None):
        pk_booking_id = request.GET['pk_booking_id']

        if pk_booking_id == 'undefined':
            booking_lines = Booking_lines.objects.all()
            return_data = []

            for booking_line in booking_lines:
                return_data.append({'pk_lines_id': booking_line.pk_lines_id, 'e_type_of_packaging': booking_line.e_type_of_packaging, 'e_item': booking_line.e_item, 'e_qty': booking_line.e_qty, 'e_weightUOM': booking_line.e_weightUOM, 'e_weightPerEach': booking_line.e_weightPerEach, 'e_dimUOM': booking_line.e_dimUOM, 'e_dimLength': booking_line.e_dimLength, 'e_dimWidth': booking_line.e_dimWidth, 'e_dimHeight': booking_line.e_dimHeight})

            return JsonResponse({'booking_lines': return_data})
        else:
            booking_lines = Booking_lines.objects.filter(fk_booking_id=pk_booking_id)
            return_data = []

            for booking_line in booking_lines:
                return_data.append({'pk_lines_id': booking_line.pk_lines_id, 'e_type_of_packaging': booking_line.e_type_of_packaging, 'e_item': booking_line.e_item, 'e_qty': booking_line.e_qty, 'e_weightUOM': booking_line.e_weightUOM, 'e_weightPerEach': booking_line.e_weightPerEach, 'e_dimUOM': booking_line.e_dimUOM, 'e_dimLength': booking_line.e_dimLength, 'e_dimWidth': booking_line.e_dimWidth, 'e_dimHeight': booking_line.e_dimHeight})

            return JsonResponse({'booking_lines': return_data})

class BookingLineDetailsView(APIView):
    def get(self, request, format=None):
        pk_booking_id = request.GET['pk_booking_id']

        if pk_booking_id == 'undefined':
            booking_line_details = Booking_lines_data.objects.all()
            return_data = []

            for booking_line_detail in booking_line_details:
                return_data.append({'modelNumber': booking_line_detail.modelNumber, 'itemDescription': booking_line_detail.itemDescription, 'quantity': booking_line_detail.quantity, 'itemFaultDescription': booking_line_detail.itemFaultDescription, 'insuranceValueEach': booking_line_detail.insuranceValueEach, 'gap_ra': booking_line_detail.gap_ra, 'clientRefNumber': booking_line_detail.clientRefNumber})

            return JsonResponse({'booking_line_details': return_data})
        else:
            booking_line_details = Booking_lines_data.objects.filter(fk_booking_id=pk_booking_id)
            return_data = []

            for booking_line_detail in booking_line_details:
                return_data.append({'modelNumber': booking_line_detail.modelNumber, 'itemDescription': booking_line_detail.itemDescription, 'quantity': booking_line_detail.quantity, 'itemFaultDescription': booking_line_detail.itemFaultDescription, 'insuranceValueEach': booking_line_detail.insuranceValueEach, 'gap_ra': booking_line_detail.gap_ra, 'clientRefNumber': booking_line_detail.clientRefNumber})

            return JsonResponse({'booking_line_details': return_data})

class BookingViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer
    
    @action(detail=False, methods=['get'])
    def get_bookings(self, request, format=None):
        clientEmp = Client_employees.objects.select_related().filter(fk_id_user = int(self.request.user.id)).first()
        client = DME_clients.objects.select_related().filter(pk_id_dme_client = int(clientEmp.fk_id_dme_client_id)).first()

        cur_date = self.request.query_params.get('date', None)
        first_date = datetime.strptime(cur_date, '%Y-%m-%d')
        last_date = (datetime.strptime(cur_date, '%Y-%m-%d')+timedelta(days=1))
        warehouse_id = self.request.query_params.get('warehouseId', None)
        sort_field = self.request.query_params.get('sortField', None)
        column_filters = json.loads(self.request.query_params.get('columnFilters', None))
        prefilter = json.loads(self.request.query_params.get('prefilterInd', None))
        # item_count_per_page = self.request.query_params.get('itemCountPerPage', 10)
        
        print('@01 - Client filter: ', client.dme_account_num)
        print('@02 - Date filter: ', cur_date, first_date, last_date)
        print('@03 - Warehouse ID filter: ', warehouse_id)
        print('@04 - Sort field: ', sort_field)
        print('@05 - Company name: ', client.company_name)
        print('@06 - Prefilter: ', prefilter)

        # Client filter
        queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)

        # Date filter
        if client.company_name  == 'Seaway':
            queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
        elif client.company_name == 'BioPak':
            queryset = queryset.filter(puPickUpAvailFrom_Date=cur_date)

        # Warehouse filter
        if int(warehouse_id) is not 0:
            queryset = queryset.filter(fk_client_warehouse=int(warehouse_id))

        # Column filter
        try:
            column_filter = column_filters['b_bookingID_Visual']
            queryset = queryset.filter(b_bookingID_Visual__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['b_dateBookedDate']
            queryset = queryset.filter(b_dateBookedDate__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['b_clientReference_RA_Numbers']
            queryset = queryset.filter(b_clientReference_RA_Numbers__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['puPickUpAvailFrom_Date']
            queryset = queryset.filter(puPickUpAvailFrom_Date__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['b_status']
            queryset = queryset.filter(b_status__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['vx_freight_provider']
            queryset = queryset.filter(vx_freight_provider__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['vx_serviceName']
            queryset = queryset.filter(vx_serviceName__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['s_05_LatestPickUpDateTimeFinal']
            queryset = queryset.filter(s_05_LatestPickUpDateTimeFinal__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['s_06_LatestDeliveryDateTimeFinal']
            queryset = queryset.filter(s_06_LatestDeliveryDateTimeFinal__contains=column_filter)
        except KeyError:
            column_filter = ''
            
        try:
            column_filter = column_filters['v_FPBookingNumber']
            queryset = queryset.filter(v_FPBookingNumber__contains=column_filter)
        except KeyError:
            column_filter = ''

        try:
            column_filter = column_filters['puCompany']
            queryset = queryset.filter(puCompany__contains=column_filter)
        except KeyError:
            column_filter = ''
            
        try:
            column_filter = column_filters['deToCompanyName']
            queryset = queryset.filter(deToCompanyName__contains=column_filter)
        except KeyError:
            column_filter = ''

        # Prefilter 0 -> all, 1 -> errors_to_correct
        if prefilter == 1:
            queryset = queryset.exclude(b_error_Capture__isnull=True).exclude(b_error_Capture__exact='')
        elif prefilter == 3:
            queryset = queryset.filter(b_status__contains='booked')

        # Sort
        if sort_field is None:
            queryset = queryset.order_by('id')
        else:
            queryset = queryset.order_by(sort_field)

        # Count
        bookings_cnt = queryset.count()
        errors_to_correct = 0
        to_manifest = 0

        # bookings = queryset[0:int(item_count_per_page)]
        bookings = queryset
        ret_data = [];

        for booking in bookings:
            if booking.b_error_Capture is not None and len(booking.b_error_Capture) > 0:
                errors_to_correct += 1
            if booking.b_status == 'booked':
                to_manifest += 1

            ret_data.append({
                'id': booking.id, 
                'b_bookingID_Visual': booking.b_bookingID_Visual, 
                'b_dateBookedDate': booking.b_dateBookedDate, 
                'puPickUpAvailFrom_Date': booking.puPickUpAvailFrom_Date, 
                'b_clientReference_RA_Numbers': booking.b_clientReference_RA_Numbers, 
                'b_status': booking.b_status, 
                'vx_freight_provider': booking.vx_freight_provider, 
                'vx_serviceName': booking.vx_serviceName, 
                's_05_LatestPickUpDateTimeFinal': booking.s_05_LatestPickUpDateTimeFinal, 
                's_06_LatestDeliveryDateTimeFinal': booking.s_06_LatestDeliveryDateTimeFinal, 
                'puCompany': booking.puCompany,
                'deToCompanyName': booking.deToCompanyName,
                'z_label_url': booking.z_label_url,
                'b_error_Capture': booking.b_error_Capture,
                'z_downloaded_shipping_label_timestamp': booking.z_downloaded_shipping_label_timestamp,
                'pk_booking_id': booking.pk_booking_id,
            })
        
        return JsonResponse({'bookings': ret_data, 'count': bookings_cnt, 'errors_to_correct': errors_to_correct, 'to_manifest': to_manifest})

    @action(detail=True, methods=['PUT'])
    def update_booking(self, request, pk, format=None):
        booking = Bookings.objects.get(pk=pk)
        serializer = BookingSerializer(booking, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # searchType = self.request.query_params.get('searchType', None)
        # keyword = str(self.request.query_params.get('keyword', None))

        # if searchType is not None:
        #     queryset = Bookings.objects.filter(Q(id__contains=keyword) | Q(b_bookingID_Visual__contains=keyword) | Q(b_dateBookedDate__contains=keyword) | Q(puPickUpAvailFrom_Date__contains=keyword) | Q(b_clientReference_RA_Numbers__contains=keyword) | Q(b_status__contains=keyword) | Q(vx_freight_provider__contains=keyword) | Q(vx_serviceName__contains=keyword) | Q(s_05_LatestPickUpDateTimeFinal__contains=keyword) | Q(s_06_LatestDeliveryDateTimeFinal__contains=keyword) | Q(v_FPBookingNumber__contains=keyword) | Q(puCompany__contains=keyword) | Q(deToCompanyName__contains=keyword))
        # else:
        #     queryset = Bookings.objects.all()

@api_view(['POST', 'GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def booking(request):
    if request.method == 'GET':
        idBookingNumber = request.GET['id']
        filterName = request.GET['filter']

        try:
            if filterName == 'dme':
                booking = Bookings.objects.get(b_bookingID_Visual=idBookingNumber)
            elif filterName == 'con':
                booking = Bookings.objects.get(v_FPBookingNumber=idBookingNumber)
            elif filterName == 'id':
                booking = Bookings.objects.get(id=idBookingNumber)
            else: 
                return JsonResponse({'booking': {}})
            nextBooking = (Bookings.objects.filter(id__gt=booking.id).order_by('id').first())
            prevBooking = (Bookings.objects.filter(id__lt=booking.id).order_by('-id').first())
            nextBookingId = -1
            prevBookingId = -1

            if nextBooking is not None:
                nextBookingId = nextBooking.id
            if prevBooking is not None:
                prevBookingId = prevBooking.id

            return_data = []

            if booking is not None:
                return_data = {'id': booking.id, 'puCompany': booking.puCompany,'pu_Address_Street_1': booking.pu_Address_Street_1, 'pu_Address_street_2': booking.pu_Address_street_2, 'pu_Address_PostalCode': booking.pu_Address_PostalCode, 'pu_Address_Suburb': booking.pu_Address_Suburb, 'pu_Address_Country': booking.pu_Address_Country, 'pu_Contact_F_L_Name': booking.pu_Contact_F_L_Name, 'pu_Phone_Main': booking.pu_Phone_Main, 'pu_Email': booking.pu_Email,'de_To_Address_Street_1': booking.de_To_Address_Street_1, 'de_To_Address_Street_2':booking.de_To_Address_Street_2, 'de_To_Address_PostalCode': booking.de_To_Address_PostalCode, 'de_To_Address_Suburb': booking.de_To_Address_Suburb, 'de_To_Address_Country': booking.de_To_Address_Country, 'de_to_Contact_F_LName': booking.de_to_Contact_F_LName, 'de_to_Phone_Main':booking.de_to_Phone_Main,  'de_Email': booking.de_Email, 'deToCompanyName': booking.deToCompanyName, 'b_bookingID_Visual': booking.b_bookingID_Visual, 'v_FPBookingNumber': booking.v_FPBookingNumber, 'pk_booking_id': booking.pk_booking_id,'vx_freight_provider': booking.vx_freight_provider}
                return JsonResponse({'booking': return_data, 'nextid': nextBookingId, 'previd': prevBookingId})
        except Bookings.DoesNotExist:
            return JsonResponse({'booking': {}})

    if request.method == 'POST':
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(self.request.user.id))
        clientWarehouseObject_list = Client_warehouses.objects.select_related().filter(fk_id_dme_client_id = int(clientEmployeObject[0].fk_id_dme_client_id)).exclude(pk_id_client_warehouses = 100)
        queryset = clientWarehouseObject_list
        return queryset

class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, filename, format=None):
        file_obj = request.FILES['file']
        user_id = request.user.id
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
        dme_account_num = clientEmployeObject[0].fk_id_dme_client.dme_account_num
        upload_file_name = request.FILES['file'].name
        prepend_name = str(dme_account_num) + '_' + upload_file_name

        save2Redis(prepend_name + "_l_000_client_acct_number", dme_account_num)
        save2Redis(prepend_name + "_b_client_name", clientEmployeObject[0].fk_id_dme_client.dme_account_num)

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
    filename = request.GET['filename']
    updatedId = request.GET['id']
    file = open('/var/www/html/dme_api/static/pdfs/{}'.format(filename), "rb")

    response = HttpResponse(
        file,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = 'attachment; filename=a.pdf'
    booking = Bookings.objects.get(pk=updatedId)
    booking.z_downloaded_shipping_label_timestamp = datetime.now()
    booking.save()
    return response

