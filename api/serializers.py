import re
from datetime import datetime

from rest_framework import serializers

from api.models import (
    Bookings,
    Client_warehouses,
    DME_employees,
    Client_employees,
    Booking_lines,
    Booking_lines_data,
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
    FP_availabilities,
    FP_costs,
    FP_pricing_rules,
    EmailLogs,
    BookingSets,
    Client_Products,
    Client_Ras,
    Utl_sql_queries,
    Client_Products,
    DME_Error,
)
from api import utils
from api.fp_apis.utils import _is_deliverable_price
from api.common import math as dme_math


class WarehouseSerializer(serializers.HyperlinkedModelSerializer):
    client_company_name = serializers.SerializerMethodField(read_only=True)

    def get_client_company_name(self, obj):
        return obj.fk_id_dme_client.company_name

    class Meta:
        model = Client_warehouses
        fields = (
            "pk_id_client_warehouses",
            "warehousename",
            "client_warehouse_code",
            "client_company_name",
        )


class SimpleBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookings
        read_only_fields = (
            "clientRefNumbers",  # property
            "gap_ras",  # property
        )
        fields = read_only_fields + (
            "id",
            "pk_booking_id",
            "b_bookingID_Visual",
            "puCompany",
            "pu_Address_Street_1",
            "pu_Address_street_2",
            "pu_Address_PostalCode",
            "pu_Address_Suburb",
            "pu_Address_Country",
            "de_To_Address_Street_1",
            "de_To_Address_Street_2",
            "de_To_Address_PostalCode",
            "de_To_Address_Suburb",
            "de_To_Address_Country",
            "deToCompanyName",
            "v_FPBookingNumber",
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
            "fk_client_warehouse",
            "b_client_warehouse_code",
            "b_clientPU_Warehouse",
            "booking_Created_For",
            "b_clientReference_RA_Numbers",
            "de_to_PickUp_Instructions_Address",
            "b_dateBookedDate",
            "z_lock_status",
            "dme_status_detail",
            "dme_status_action",
            "puPickUpAvailFrom_Date",
            "pu_PickUp_By_Date",
            "de_Deliver_From_Date",
            "de_Deliver_By_Date",
            "b_client_sales_inv_num",
            "b_client_name_sub",
            "x_manual_booked_flag",
            "b_fp_qty_delivered",
            "manifest_timestamp",
            "b_booking_project",
            "z_calculated_ETA",
            "b_project_due_date",
            "delivery_booking",
            "fp_store_event_date",
            "fp_store_event_time",
            "fp_store_event_desc",
            "fp_received_date_time",
            "b_given_to_transport_date_time",
            "z_downloaded_shipping_label_timestamp",
            "api_booking_quote",
            "b_status_API",
            "b_error_Capture",
            "kf_client_id",
            "z_locked_status_time",
        )


class BookingSerializer(serializers.ModelSerializer):
    eta_pu_by = serializers.SerializerMethodField(read_only=True)
    eta_de_by = serializers.SerializerMethodField(read_only=True)
    pricing_cost = serializers.SerializerMethodField(read_only=True)
    pricing_service_name = serializers.SerializerMethodField(read_only=True)
    pricing_account_code = serializers.SerializerMethodField(read_only=True)

    def get_eta_pu_by(self, obj):
        return utils.get_eta_pu_by(obj)

    def get_eta_de_by(self, obj):
        if obj.api_booking_quote:
            return utils.get_eta_de_by(obj, obj.api_booking_quote)

        return None

    def get_pricing_cost(self, obj):
        if obj.api_booking_quote:
            return obj.api_booking_quote.client_mu_1_minimum_values

        return None

    def get_pricing_service_name(self, obj):
        if obj.api_booking_quote:
            return obj.api_booking_quote.service_name

        return None

    def get_pricing_account_code(self, obj):
        if obj.api_booking_quote:
            return obj.api_booking_quote.account_code

        return None

    class Meta:
        model = Bookings
        read_only_fields = (
            "eta_pu_by",  # serializer method
            "eta_de_by",  # serializer method
            "pricing_cost",  # serializer method
            "pricing_account_code",  # serializer method
            "pricing_service_name",  # serializer method
            "business_group",  # property
            "dme_delivery_status_category",  # property
            "client_item_references",  # property
            "clientRefNumbers",  # property
            "gap_ras",  # property
        )
        fields = read_only_fields + (
            "id",
            "pk_booking_id",
            "b_bookingID_Visual",
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
            "pu_Comm_Booking_Communicate_Via",
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
            "de_To_Comm_Delivery_Communicate_Via",
            "v_FPBookingNumber",
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
            "fk_client_warehouse",
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
            "z_lock_status",
            "tally_delivered",
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
            "inv_sell_quoted_override",
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
            "z_downloaded_shipping_label_timestamp",
            "api_booking_quote",
            "vx_futile_Booking_Notes",
            "s_05_Latest_Pick_Up_Date_TimeSet",
            "s_06_Latest_Delivery_Date_TimeSet",
            "b_handling_Instructions",
            "b_status_API",
            "b_booking_Notes",
            "b_error_Capture",
            "kf_client_id",
            "z_locked_status_time",
            "x_booking_Created_With",
            "z_CreatedByAccount",
            "b_send_POD_eMail",
        )


class BookingLineSerializer(serializers.ModelSerializer):
    is_scanned = serializers.SerializerMethodField(read_only=True)

    def get_is_scanned(self, obj):
        return obj.get_is_scanned()

    class Meta:
        model = Booking_lines
        fields = (
            "pk_lines_id",
            "fk_booking_id",
            "pk_booking_lines_id",
            "e_type_of_packaging",
            "e_item",
            "e_qty",
            "e_weightUOM",
            "e_weightPerEach",
            "e_dimUOM",
            "e_dimLength",
            "e_dimWidth",
            "e_dimHeight",
            "e_Total_KG_weight",
            "e_1_Total_dimCubicMeter",
            "total_2_cubic_mass_factor_calc",
            "e_qty_awaiting_inventory",
            "e_qty_collected",
            "e_qty_scanned_depot",
            "e_qty_delivered",
            "e_qty_adjusted_delivered",
            "e_qty_damaged",
            "e_qty_returned",
            "e_qty_shortages",
            "e_qty_scanned_fp",
            "is_scanned",
            "picked_up_timestamp",
        )


class BookingLineDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking_lines_data
        fields = (
            "pk_id_lines_data",
            "fk_booking_id",
            "fk_booking_lines_id",
            "modelNumber",
            "itemDescription",
            "quantity",
            "itemFaultDescription",
            "insuranceValueEach",
            "gap_ra",
            "clientRefNumber",
        )


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dme_status_history
        fields = "__all__"


class DmeReportsSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField(read_only=True)

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
    eta_pu_by = serializers.SerializerMethodField(read_only=True)
    eta_de_by = serializers.SerializerMethodField(read_only=True)
    is_deliverable = serializers.SerializerMethodField(read_only=True)

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
        try:
            booking = self.context.get("booking")
            return utils.get_eta_pu_by(booking)
        except Exception as e:
            return None

    def get_eta_de_by(self, obj):
        try:
            booking = self.context.get("booking")
            return utils.get_eta_de_by(booking, obj)
        except Exception as e:
            return None

    def get_is_deliverable(self, obj):
        try:
            booking = self.context.get("booking")
            return _is_deliverable_price(obj, booking)
        except Exception as e:
            return None

    class Meta:
        model = API_booking_quotes
        fields = "__all__"


class SimpleQuoteSerializer(serializers.ModelSerializer):
    cost_id = serializers.SerializerMethodField(read_only=True)
    eta = serializers.SerializerMethodField(read_only=True)
    cost = serializers.SerializerMethodField(read_only=True)
    fp_name = serializers.SerializerMethodField(read_only=True)

    def get_cost_id(self, obj):
        return obj.pk

    def get_cost(self, obj):
        if obj.tax_value_1:
            return dme_math.ceil(obj.client_mu_1_minimum_values + obj.tax_value_1, 2)
        else:
            return dme_math.ceil(obj.client_mu_1_minimum_values, 2)

    def get_eta(self, obj):
        return obj.etd

    def get_fp_name(self, obj):
        return obj.fk_freight_provider_id

    class Meta:
        model = API_booking_quotes
        fields = ("cost_id", "cost", "eta", "service_name", "fp_name")


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
        fields = (
            "id",
            "fp_company_name",
            "fp_address_country",
            "service_cutoff_time",
            "rule_type",
            "rule_type_code",
        )


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
        fields = (
            "id",
            "option_value",
            "option_name",
            "option_description",
            "elapsed_seconds",
            "is_running",
            "arg1",
            "arg2",
        )


class FilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Files
        fields = "__all__"


class VehiclesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FP_vehicles
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


class ClientEmployeesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client_employees
        fields = "__all__"


class SqlQueriesSerializer(serializers.ModelSerializer):
    sql_query = serializers.CharField()

    def validate_sql_query(self, value):
        """
        Only SELECT query is allowed to added
        """
        if re.search("select", value, flags=re.IGNORECASE):
            return value
        else:
            raise serializers.ValidationError("Only SELECT query is allowed!")

    class Meta:
        model = Utl_sql_queries
        fields = "__all__"


class ClientProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client_Products
        fields = "__all__"


class ClientRasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client_Ras
        fields = "__all__"


class BookingSetsSerializer(serializers.ModelSerializer):
    bookings_cnt = serializers.SerializerMethodField(read_only=True)

    def get_bookings_cnt(self, obj):
        if obj.booking_ids:
            return len(obj.booking_ids.split(", "))

        return 0

    class Meta:
        model = BookingSets
        fields = "__all__"


class ErrorSerializer(serializers.ModelSerializer):
    fp_name = serializers.SerializerMethodField(read_only=True)

    def get_fp_name(self, obj):
        return obj.freight_provider.fp_company_name

    class Meta:
        model = DME_Error
        fields = (
            "accountCode",
            "error_code",
            "error_description",
            "fp_name",
        )
