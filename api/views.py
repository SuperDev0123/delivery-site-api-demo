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
        # item_count_per_page = self.request.query_params.get('itemCountPerPage', 10)
        
        print('@01 - Client filter: ', client.dme_account_num)
        print('@02 - Date filter: ', first_date, last_date)
        print('@03 - Warehouse ID filter: ', warehouse_id)
        print('@04 - Sort field: ', sort_field)
        print('@05 - Column filter: ', column_filters)

        # Client filter
        queryset = Bookings.objects.filter(kf_client_id=client.dme_account_num)

        # Date filter
        queryset = queryset.filter(z_CreatedTimestamp__range=(first_date, last_date))
        
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
                'vx_serviceName': booking.vx_serviceName, 
                's_05_LatestPickUpDateTimeFinal': booking.s_05_LatestPickUpDateTimeFinal, 
                's_06_LatestDeliveryDateTimeFinal': booking.s_06_LatestDeliveryDateTimeFinal, 
                'puCompany': booking.puCompany,
                'deToCompanyName': booking.deToCompanyName,
            })
        
        return JsonResponse({'bookings': ret_data, 'count': bookings_cnt})

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

@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((AllowAny,))
def booking(request):
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
    file = open('/var/www/html/dme_api/static/pdfs/{}'.format(filename), "rb")

    response = HttpResponse(
        file,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = 'attachment; filename=a.pdf'

    return response
