from pages.models import Bookings, Client_warehouse, DME_employees, Client_employees
from rest_framework import serializers

class WarehouseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Client_warehouse
        fields = ('pk_id_client_warehouse', 'warehousename', 'warehouse_address1', 'warehouse_address2', 'warehouse_state', 'warehouse_suburb', 'warehouse_phone_main', 'warehouse_hours')

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookings
        fields = '__all__'
        # fields = ('id', 'b_bookingID_Visual', 'b_dateBookedDate', 'puPickUpAvailFrom_Date', 'b_clientReference_RA_Numbers', 'b_status', 'vx_freight_provider', 'vx_serviceName', 's_05_LatestPickUpDateTimeFinal', 's_06_LatestDeliveryDateTimeFinal', 'v_FPBookingNumber', 'puCompany', 'deToCompanyName', 'consignment_label_link', 'error_details')