from pages.models import bookings
from rest_framework import serializers

class BookingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = bookings
        fields = ('id', 'b_bookingID_Visual', 'b_dateBookedDate', 'puPickUpAvailFrom_Date', 'b_clientReference_RA_Numbers', 'b_status', 'vx_freight_provider', 'vx_serviceName', 's_05_LatestPickUpDateTimeFinal', 's_06_LatestDeliveryDateTimeFinal', 'v_FPBookingNumber', 'puCompany', 'deToCompanyName')