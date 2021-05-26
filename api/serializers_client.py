from rest_framework import serializers
from .models import (
    BOK_0_BookingKeys,
    BOK_1_headers,
    BOK_2_lines,
    BOK_3_lines_data,
    DME_clients,
)
from .validators import should_have_value, should_have_positive_value


class BOK_0_Serializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_0_BookingKeys
        fields = "__all__"


class BOK_1_Serializer(serializers.ModelSerializer):
    client_booking_id = serializers.CharField(max_length=64)
    fk_client_id = serializers.CharField(validators=[should_have_value])
    b_client_warehouse_code = serializers.CharField(validators=[should_have_value])
    b_clientPU_Warehouse = serializers.CharField(validators=[should_have_value])
    b_059_b_del_address_postalcode = serializers.CharField(
        validators=[should_have_value]
    )
    success = serializers.CharField(validators=[should_have_value])
    b_client_name = serializers.SerializerMethodField(read_only=True)

    def get_b_client_name(self, obj):
        return DME_clients.objects.get(dme_account_num=obj.fk_client_id).company_name

    class Meta:
        model = BOK_1_headers
        fields = (
            "pk_auto_id",
            "pk_header_id",
            "client_booking_id",
            "b_client_name",
            "fk_client_id",
            "b_client_warehouse_code",
            "b_clientPU_Warehouse",
            "fk_client_warehouse",
            "b_000_1_b_clientReference_RA_Numbers",
            "b_000_2_b_price",
            "b_001_b_freight_provider",
            "b_002_b_vehicle_type",
            "b_003_b_service_name",
            "b_005_b_created_for",
            "b_006_b_created_for_email",
            "b_007_b_ready_status",
            "b_008_b_category",
            "b_009_b_priority",
            "b_010_b_notes",
            "b_012_b_driver_bring_connote",
            "b_013_b_package_job",
            "b_014_b_pu_handling_instructions",
            "b_016_b_pu_instructions_address",
            "b_019_b_pu_tail_lift",
            "b_021_b_pu_avail_from_date",
            "b_022_b_pu_avail_from_time_hour",
            "b_023_b_pu_avail_from_time_minute",
            "b_024_b_pu_by_date",
            "b_025_b_pu_by_time_hour",
            "b_026_b_pu_by_time_minute",
            "b_027_b_pu_address_type",
            "b_028_b_pu_company",
            "b_029_b_pu_address_street_1",
            "b_030_b_pu_address_street_2",
            "b_031_b_pu_address_state",
            "b_032_b_pu_address_suburb",
            "b_033_b_pu_address_postalcode",
            "b_034_b_pu_address_country",
            "b_035_b_pu_contact_full_name",
            "b_037_b_pu_email",
            "b_038_b_pu_phone_main",
            "b_040_b_pu_communicate_via",
            "b_041_b_del_tail_lift",
            "b_042_b_del_num_operators",
            "b_043_b_del_instructions_contact",
            "b_044_b_del_instructions_address",
            "b_047_b_del_avail_from_date",
            "b_048_b_del_avail_from_time_hour",
            "b_049_b_del_avail_from_time_minute",
            "b_050_b_del_by_date",
            "b_051_b_del_by_time_hour",
            "b_052_b_del_by_time_minute",
            "b_053_b_del_address_type",
            "b_054_b_del_company",
            "b_055_b_del_address_street_1",
            "b_056_b_del_address_street_2",
            "b_057_b_del_address_state",
            "b_058_b_del_address_suburb",
            "b_059_b_del_address_postalcode",
            "b_060_b_del_address_country",
            "b_061_b_del_contact_full_name",
            "b_063_b_del_email",
            "b_064_b_del_phone_main",
            "b_066_b_del_communicate_via",
            "b_065_b_del_phone_mobile",
            "b_067_assembly_required",
            "b_068_b_del_location",
            "b_069_b_del_floor_number",
            "b_070_b_del_floor_access_by",
            "b_071_b_del_sufficient_space",
            "b_072_b_pu_no_of_assists",
            "b_073_b_del_no_of_assists",
            "b_074_b_pu_access",
            "b_075_b_del_access",
            "b_076_b_pu_service",
            "b_077_b_del_service",
            "b_078_b_pu_location",
            "b_079_b_pu_floor_number",
            "b_080_b_pu_floor_access_by",
            "b_081_b_pu_auto_pack",
            "b_000_3_consignment_number",
            "success",
            "x_booking_Created_With",
            "quote_id",
            "b_client_order_num",
            "b_client_sales_inv_num",
        )


class BOK_2_Serializer(serializers.ModelSerializer):
    l_002_qty = serializers.FloatField(validators=[should_have_positive_value])
    l_005_dim_length = serializers.FloatField(validators=[should_have_positive_value])
    l_006_dim_width = serializers.FloatField(validators=[should_have_positive_value])
    l_007_dim_height = serializers.FloatField(validators=[should_have_positive_value])
    l_009_weight_per_each = serializers.FloatField(
        validators=[should_have_positive_value]
    )
    fk_header_id = serializers.CharField(validators=[should_have_value])
    success = serializers.CharField(validators=[should_have_value])
    # Sequence
    zbl_121_integer_1 = serializers.IntegerField(required=False)

    class Meta:
        model = BOK_2_lines
        fields = (
            "l_001_type_of_packaging",
            "l_002_qty",
            "l_003_item",
            "l_004_dim_UOM",
            "l_005_dim_length",
            "l_006_dim_width",
            "l_007_dim_height",
            "l_008_weight_UOM",
            "l_009_weight_per_each",
            "success",
            "fk_header_id",
            "v_client_pk_consigment_num",
            "pk_booking_lines_id",
            "e_item_type",
            "zbl_121_integer_1",  # Sequence
            "zbl_102_text_2",  # ProductGroupCode
        )


class BOK_3_Serializer(serializers.ModelSerializer):
    success = serializers.CharField(validators=[should_have_value])

    class Meta:
        model = BOK_3_lines_data
        fields = "__all__"
