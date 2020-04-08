from rest_framework import serializers

from api.models import (
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
    DME_Email_Templates,
    Fp_freight_providers,
    FP_carriers,
    FP_zones,
    DME_Options,
    DME_Files,
    FP_vehicles,
    FP_timings,
    FP_availabilities,
    FP_costs,
    FP_pricing_rules,
    EmailLogs,
    BookingSets,
)
from api import utils


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
    eta_pu_by = serializers.SerializerMethodField()
    eta_de_by = serializers.SerializerMethodField()

    def get_eta_pu_by(self, obj):
        return utils.get_eta_pu_by(obj)

    def get_eta_de_by(self, obj):
        if obj.api_booking_quote:
            return utils.get_eta_de_by(obj, obj.api_booking_quote)

        return None

    class Meta:
        model = Bookings
        fields = (
            "id",
            "puCompany",
            "pu_Address_Street_1",
            "pu_Address_street_2",
            "pu_Address_PostalCode",
            "pu_Address_Suburb",
            "pu_Address_Country",
            "pu_Contact_F_L_Name",
            "pu_Phone_Main",
            "pu_Email",
            "pu_email_Group_Name",
            "pu_email_Group",
            "de_To_Address_Street_1",
            "de_To_Address_Street_2",
            "de_To_Address_PostalCode",
            "de_To_Address_Suburb",
            "de_To_Address_Country",
            "de_to_Contact_F_LName",
            "de_to_Phone_Main",
            "de_Email",
            "de_Email_Group_Name",
            "de_Email_Group_Emails",
            "deToCompanyName",
            "b_bookingID_Visual",
            "v_FPBookingNumber",
            "pk_booking_id",
            "vx_freight_provider",
            "z_label_url",
            "z_pod_url",
            "z_pod_signed_url",
            "pu_Address_State",
            "de_To_Address_State",
            "b_status",
            "b_dateBookedDate",
            "s_20_Actual_Pickup_TimeStamp",
            "s_21_Actual_Delivery_TimeStamp",
            "b_client_name",
            "b_client_warehouse_code",
            "b_clientPU_Warehouse",
            "booking_Created_For",
            "booking_Created_For_Email",
            "b_booking_Category",
            "b_booking_Priority",
            "vx_fp_pu_eta_time",
            "vx_fp_del_eta_time",
            "b_clientReference_RA_Numbers",
            "de_to_Pick_Up_Instructions_Contact",
            "de_to_PickUp_Instructions_Address",
            "pu_pickup_instructions_address",
            "pu_PickUp_Instructions_Contact",
            "consignment_label_link",
            "s_02_Booking_Cutoff_Time",
            "z_CreatedTimestamp",
            "b_dateBookedDate",
            "total_lines_qty_override",
            "total_1_KG_weight_override",
            "total_Cubic_Meter_override",
            "b_status_API",
            "z_lock_status",
            "tally_delivered",
            "dme_status_history_notes",
            "dme_status_detail",
            "dme_status_action",
            "dme_status_linked_reference_from_fp",
            "puPickUpAvailFrom_Date",
            "pu_PickUp_Avail_Time_Hours",
            "pu_PickUp_Avail_Time_Minutes",
            "pu_PickUp_By_Date",
            "pu_PickUp_By_Time_Hours",
            "pu_PickUp_By_Time_Minutes",
            "de_Deliver_From_Date",
            "de_Deliver_From_Hours",
            "de_Deliver_From_Minutes",
            "de_Deliver_By_Date",
            "de_Deliver_By_Hours",
            "de_Deliver_By_Minutes",
            "client_item_references",
            "eta_pu_by",
            "eta_de_by",
            "v_service_Type",
            "vx_serviceName",
            "vx_account_code",
            "fk_fp_pickup_id",
            "v_vehicle_Type",
            "inv_billing_status",
            "inv_billing_status_note",
            "b_client_sales_inv_num",
            "b_client_order_num",
            "b_client_name_sub",
            "inv_dme_invoice_no",
            "fp_invoice_no",
            "inv_cost_quoted",
            "inv_cost_actual",
            "inv_sell_quoted",
            "inv_sell_actual",
            "x_manual_booked_flag",
            "b_fp_qty_delivered",
            "manifest_timestamp",
            "b_booking_project",
            "b_project_opened",
            "b_project_inventory_due",
            "b_project_wh_unpack",
            "b_project_dd_receive_date",
            "z_calculated_ETA",
            "b_project_due_date",
            "delivery_booking",
            "fp_store_event_date",
            "fp_store_event_time",
            "fp_store_event_desc",
            "fp_received_date_time",
            "b_given_to_transport_date_time",
            "x_ReadyStatus",
            "api_booking_quote",
            "vx_futile_Booking_Notes",
            "s_05_Latest_Pick_Up_Date_TimeSet",
            "s_06_Latest_Delivery_Date_TimeSet",
            "has_comms",  # property
            "business_group",  # property
            "dme_delivery_status_category",  # property
            "client_item_references",  # property
            "clientRefNumbers",  # property
        )


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
    eta_pu_by = serializers.SerializerMethodField()
    eta_de_by = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields_to_exclude' arg up to the superclass
        fields_to_exclude = kwargs.pop("fields_to_exclude", None)

        # Instantiate the superclass normally
        super(ApiBookingQuotesSerializer, self).__init__(*args, **kwargs)

        if fields_to_exclude is not None:
            disallowed = set(fields_to_exclude)
            for field_name in disallowed:
                self.fields.pop(field_name)

    def get_eta_pu_by(self, obj):
        booking = Bookings.objects.get(pk_booking_id=obj.fk_booking_id)
        return utils.get_eta_pu_by(booking)

    def get_eta_de_by(self, obj):
        booking = Bookings.objects.get(pk_booking_id=obj.fk_booking_id)
        return utils.get_eta_de_by(booking, obj)

    class Meta:
        model = API_booking_quotes
        fields = "__all__"


class EmailTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Email_Templates
        fields = "__all__"


class FpSerializer(serializers.ModelSerializer):
    rule_type_code = serializers.SerializerMethodField(read_only=True)

    def get_rule_type_code(self, fp):
        if fp.rule_type:
            return fp.rule_type.rule_type_code
        else:
            return None

    class Meta:
        model = Fp_freight_providers
        fields = "__all__"


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_carriers
        fields = "__all__"


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_zones
        fields = "__all__"


class OptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Options
        fields = "__all__"


class FilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Files
        fields = "__all__"


class VehiclesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_vehicles
        fields = "__all__"


class TimingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_timings
        fields = "__all__"


class AvailabilitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_availabilities
        fields = "__all__"


class CostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_costs
        fields = "__all__"


class PricingRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_pricing_rules
        fields = "__all__"


class EmailLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLogs
        fields = "__all__"


class BookingSetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingSets
        fields = "__all__"
