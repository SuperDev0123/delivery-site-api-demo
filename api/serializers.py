from rest_framework import serializers
from .models import Bookings, Client_warehouses, DME_employees, Client_employees, Booking_lines, Booking_lines_data

class WarehouseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Client_warehouses
        fields = ('pk_id_client_warehouses', 'warehousename', 'warehouse_address1', 'warehouse_address2', 'warehouse_state', 'warehouse_suburb', 'warehouse_phone_main', 'warehouse_hours')

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookings
        fields = '__all__'

class BookingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking_lines
        fields = '__all__'

class BookingLineDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking_lines_data
        fields = '__all__'
