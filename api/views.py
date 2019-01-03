from django.shortcuts import render
from rest_framework import views, status
from django.core import serializers
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from django.http import JsonResponse
from django.http import QueryDict
from django.db.models import Q

from api.serializers import BookingSerializer, WarehouseSerializer
from .models import *
from .utils import clearFileCheckHistory, getFileCheckHistory, save2Redis

class UserView(APIView):
    def post(self, request, format=None):
        return JsonResponse({'username': request.user.username})

class BookingLinesView(APIView):
    def get(self, request, format=None):
        booking_id = request.GET['booking_id']
        booking_lines = Booking_lines.objects.filter(fk_booking_id=int(booking_id))
        return_data = []

        for booking_line in booking_lines:
            return_data.append({'pk_auto_id_lines': booking_line.pk_auto_id_lines, 'e_type_of_packaging': booking_line.e_type_of_packaging, 'e_item': booking_line.e_item, 'e_qty': booking_line.e_qty, 'e_weightUOM': booking_line.e_weightUOM, 'e_weightPerEach': booking_line.e_weightPerEach, 'e_dimUOM': booking_line.e_dimUOM, 'e_dimLength': booking_line.e_dimLength, 'e_dimWidth': booking_line.e_dimWidth, 'e_dimHeight': booking_line.e_dimHeight})

        return JsonResponse({'booking_lines': return_data})

class BookingLineDetailsView(APIView):
    def get(self, request, format=None):
        booking_line_id = request.GET['booking_line_id']
        booking_line_details = Booking_lines_data.objects.filter(fk_id_booking_lines=int(booking_line_id))
        return_data = []

        for booking_line_detail in booking_line_details:
            return_data.append({'modelNumber': booking_line_detail.modelNumber, 'itemDescription': booking_line_detail.itemDescription, 'quantity': booking_line_detail.quantity, 'itemFaultDescription': booking_line_detail.itemFaultDescription, 'insuranceValueEach': booking_line_detail.insuranceValueEach, 'gap_ra': booking_line_detail.gap_ra, 'clientRefNumber': booking_line_detail.clientRefNumber})

        return JsonResponse({'booking_line_details': return_data})

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        searchType = self.request.query_params.get('searchType', None)
        keyword = self.request.query_params.get('keyword', None)

        clientEmp = Client_employees.objects.select_related().filter(fk_id_user = int(self.request.user.id)).first()
        clientWarehouses = Client_warehouses.objects.select_related().filter(fk_id_dme_client_id = int(clientEmp.fk_id_dme_client_id))

        if searchType is not None:
            if keyword.isdigit():
                queryset = Bookings.objects.filter(Q(id__contains=keyword) | Q(b_bookingID_Visual=keyword) | Q(b_dateBookedDate__contains=keyword) | Q(puPickUpAvailFrom_Date__contains=keyword) | Q(b_clientReference_RA_Numbers=keyword) | Q(b_status__contains=keyword) | Q(vx_freight_provider__contains=keyword) | Q(vx_serviceName__contains=keyword) | Q(s_05_LatestPickUpDateTimeFinal__contains=keyword) | Q(s_06_LatestDeliveryDateTimeFinal__contains=keyword) | Q(v_FPBookingNumber__contains=keyword) | Q(puCompany__contains=keyword) | Q(deToCompanyName__contains=keyword))
            else:
                queryset = Bookings.objects.filter(Q(id__contains=keyword) | Q(b_dateBookedDate__contains=keyword) | Q(puPickUpAvailFrom_Date__contains=keyword) | Q(b_clientReference_RA_Numbers=keyword) | Q(b_status__contains=keyword) | Q(vx_freight_provider__contains=keyword) | Q(vx_serviceName__contains=keyword) | Q(s_05_LatestPickUpDateTimeFinal__contains=keyword) | Q(s_06_LatestDeliveryDateTimeFinal__contains=keyword) | Q(v_FPBookingNumber__contains=keyword) | Q(puCompany__contains=keyword) | Q(deToCompanyName__contains=keyword))
        else:
            queryset = Bookings.objects.all()

        retData = []

        for x in queryset:
            for y in clientWarehouses:
                if (x.b_clientPU_Warehouse == y):
                    retData.append(x)

        return retData

    def update(self, request, pk, format=None):
        booking = Bookings.objects.get(pk=pk)
        serializer = BookingSerializer(booking, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(self.request.user.id))
        clientWarehouseObject_list = Client_warehouses.objects.select_related().filter(fk_id_dme_client_id = int(clientEmployeObject[0].fk_id_dme_client_id))
        queryset = clientWarehouseObject_list
        return queryset

class FileUploadView(views.APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, filename, format=None):
        file_obj = request.FILES['file']
        user_id = request.user.id
        clientEmployeObject = Client_employees.objects.select_related().filter(fk_id_user = int(user_id))
        dme_account_num = clientEmployeObject[0].fk_id_dme_client.dme_account_num
        warehouse_id = request.POST.get('warehouse_id')
        clientWarehouseObject = Client_warehouses.objects.filter(pk_id_client_warehouses__contains=warehouse_id)
        upload_file_name = request.FILES['file'].name
        prepend_name = str(dme_account_num) + '_' + upload_file_name

        save2Redis(prepend_name + "l_000_client_acct_number", dme_account_num)
        save2Redis(prepend_name + "l_011_client_warehouse_id", warehouse_id)
        save2Redis(prepend_name + "l_012_client_warehouse_name", clientWarehouseObject[0].warehousename)

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

    if len(result) == 0:
        return JsonResponse({'status_code': 1})
    else:
        return JsonResponse({'status_code': 2, 'errors': result})
