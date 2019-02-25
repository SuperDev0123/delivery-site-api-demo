from rest_framework import serializers
from .models import Bookings, Client_warehouses, DME_employees, Client_employees

class WarehouseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Client_warehouses
        fields = ('pk_id_client_warehouses', 'warehousename', 'warehouse_address1', 'warehouse_address2', 'warehouse_state', 'warehouse_suburb', 'warehouse_phone_main', 'warehouse_hours')

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookings
        # fields = ('id', 'b_bookingID_Visual', 'z_downloaded_shipping_label_timestamp', 'b_dateBookedDate', 'puPickUpAvailFrom_Date', 'b_clientReference_RA_Numbers', 'b_status', 'vx_freight_provider', 'vx_serviceName', 's_05_LatestPickUpDateTimeFinal', 's_06_LatestDeliveryDateTimeFinal', 'v_FPBookingNumber', 'puCompany', 'deToCompanyName')
        fields = '__all__'