from rest_framework import serializers
from .models import (
    Bookings,
    Client_warehouses,
    DME_employees,
    Client_employees,
    Booking_lines,
    Booking_lines_data,
    Dme_comm_and_task,
    Dme_comm_notes,
    Dme_status_history,
    DME_reports,
    API_booking_quotes,
    FP_Store_Booking_Log,
    DME_Files
)


class WarehouseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Client_warehouses
        fields = (
            "pk_id_client_warehouses",
            "warehousename",
            "warehouse_address1",
            "warehouse_address2",
            "warehouse_state",
            "warehouse_suburb",
            "warehouse_phone_main",
            "warehouse_hours",
            "type",
            "client_warehouse_code",
        )


class BookingSerializer(serializers.ModelSerializer):
    client_item_references = serializers.SerializerMethodField()

    def get_client_item_references(self, obj):
        return Bookings.get_client_item_references(obj)

    class Meta:
        model = Bookings
        fields = "__all__"


class BookingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking_lines
        fields = "__all__"


class BookingLineDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking_lines_data
        fields = "__all__"


class CommSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dme_comm_and_task
        fields = "__all__"


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dme_comm_notes
        fields = "__all__"


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dme_status_history
        fields = "__all__"


class DmeReportsSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = DME_reports
        fields = "__all__"

    def get_username(self, obj):
        return obj.user.username


class FPStoreBookingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_Store_Booking_Log
        fields = "__all__"


class ApiBookingQuotesSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields_to_exclude' arg up to the superclass
        fields_to_exclude = kwargs.pop("fields_to_exclude", None)

        # Instantiate the superclass normally
        super(ApiBookingQuotesSerializer, self).__init__(*args, **kwargs)

        if fields_to_exclude is not None:
            disallowed = set(fields_to_exclude)
            for field_name in disallowed:
                self.fields.pop(field_name)

    class Meta:
        model = API_booking_quotes
        fields = "__all__"


class DME_Files_Serializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Files
        fields = "__all__"
