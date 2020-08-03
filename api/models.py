import pytz
import logging
from datetime import datetime, date, timedelta, time

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext as _
from django_base64field.fields import Base64Field
from django.contrib.auth.models import BaseUserManager
from django.db.models import Max
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from api.common import trace_error

logger = logging.getLogger("dme_api")


class UserPermissions(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1
    )
    can_create_comm = models.BooleanField(blank=True, null=True, default=False)

    class Meta:
        db_table = "user_permissions"


class DME_Roles(models.Model):
    id = models.AutoField(primary_key=True)
    role_code = models.CharField(
        verbose_name=_("Role Code"), max_length=32, blank=False
    )
    description = models.CharField(
        verbose_name=_("Role Description"), max_length=255, blank=False
    )

    class Meta:
        db_table = "dme_roles"


class DME_clients(models.Model):
    pk_id_dme_client = models.AutoField(primary_key=True)
    company_name = models.CharField(
        verbose_name=_("Company Name"), max_length=128, blank=False, null=False
    )
    dme_account_num = models.CharField(
        verbose_name=_("dme account num"), max_length=64, default="", null=False
    )
    phone = models.IntegerField(verbose_name=_("phone number"))
    client_filter_date_field = models.CharField(
        verbose_name=_("Client Filter Date Field"),
        max_length=64,
        blank=False,
        null=False,
        default="z_CreatedTimestamp",
    )
    current_freight_provider = models.CharField(
        verbose_name=_("Related FP"), max_length=30, blank=False, null=True, default="*"
    )
    client_mark_up_percent = models.FloatField(default=0, null=True, blank=True)
    client_min_markup_startingcostvalue = models.FloatField(
        default=0, null=True, blank=True
    )
    client_min_markup_value = models.FloatField(default=0, null=True, blank=True)
    augment_pu_by_time = models.TimeField(blank=True, null=True, default=None)
    augment_pu_available_time = models.TimeField(blank=True, null=True, default=None)

    class Meta:
        db_table = "dme_clients"


class DME_employees(models.Model):
    pk_id_dme_emp = models.AutoField(primary_key=True)
    fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name_last = models.CharField(
        verbose_name=_("last name"), max_length=30, blank=False
    )
    name_first = models.CharField(
        verbose_name=_("first name"), max_length=30, blank=False
    )
    role = models.ForeignKey(DME_Roles, on_delete=models.CASCADE, default=1)
    warehouse_id = models.IntegerField(
        verbose_name=_("Warehouse ID"), default=1, blank=False, null=True
    )
    status_time = models.DateTimeField(
        verbose_name=_("Status Time"), default=datetime.now, blank=True
    )

    class Meta:
        db_table = "dme_employees"


class Client_warehouses(models.Model):
    pk_id_client_warehouses = models.AutoField(primary_key=True)
    fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
    warehousename = models.CharField(
        verbose_name=_("warehoursename"),
        max_length=230,
        blank=False,
        null=True,
        default="",
    )
    warehouse_address1 = models.CharField(
        verbose_name=_("warehouse address1"),
        max_length=255,
        blank=False,
        null=True,
        default="",
    )
    warehouse_address2 = models.CharField(
        verbose_name=_("warehouse address2"),
        max_length=255,
        blank=False,
        null=True,
        default="",
    )
    warehouse_state = models.CharField(
        verbose_name=_("warehouse state"),
        max_length=64,
        blank=False,
        null=True,
        default="",
    )
    warehouse_suburb = models.CharField(
        verbose_name=_("warehouse suburb"),
        max_length=255,
        blank=False,
        null=True,
        default="",
    )
    warehouse_phone_main = models.CharField(
        verbose_name=_("warehouse phone number"),
        max_length=16,
        blank=False,
        null=True,
        default="",
    )
    warehouse_postal_code = models.CharField(
        verbose_name=_("warehouse postal code"),
        max_length=64,
        blank=False,
        null=True,
        default="",
    )
    warehouse_hours = models.IntegerField(verbose_name=_("warehouse hours"))
    type = models.CharField(
        verbose_name=_("warehouse type"), max_length=30, blank=True, null=True
    )
    client_warehouse_code = models.CharField(
        verbose_name=_("warehouse code"), max_length=100, blank=True, null=True
    )
    success_type = models.IntegerField(default=0)

    class Meta:
        db_table = "dme_client_warehouses"


class Client_employees(models.Model):
    pk_id_client_emp = models.AutoField(primary_key=True)
    fk_id_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True
    )
    fk_id_dme_client = models.ForeignKey(
        DME_clients, on_delete=models.CASCADE, blank=True, null=True
    )
    role = models.ForeignKey(DME_Roles, on_delete=models.CASCADE, blank=True, null=True)
    name_last = models.CharField(
        verbose_name=_("last name"), max_length=30, blank=True, null=True
    )
    name_first = models.CharField(
        verbose_name=_("first name"), max_length=30, blank=True, null=True
    )
    email = models.EmailField(
        verbose_name=_("email address"), max_length=64, unique=True, null=True
    )
    phone = models.IntegerField(verbose_name=_("phone number"), blank=True, null=True)
    warehouse_id = models.IntegerField(
        verbose_name=_("Warehouse ID"), default=1, blank=True, null=True
    )
    clientEmployeeSalutation = models.CharField(max_length=20, blank=True, null=True)
    client_emp_name_frst = models.CharField(max_length=50, blank=True, null=True)
    client_emp_name_surname = models.CharField(max_length=50, blank=True, null=True)
    clientEmployeeEmail = models.CharField(max_length=50, blank=True, null=True)
    clien_emp_job_title = models.CharField(max_length=50, blank=True, null=True)
    client_emp_phone_fax = models.CharField(max_length=50, blank=True, null=True)
    client_emp_phone_main = models.CharField(max_length=50, blank=True, null=True)
    client_emp_phone_mobile = models.CharField(max_length=50, blank=True, null=True)
    client_emp_address_1 = models.CharField(max_length=200, blank=True, null=True)
    client_emp_address_2 = models.CharField(max_length=200, blank=True, null=True)
    client_emp_address_state = models.CharField(max_length=50, blank=True, null=True)
    client_emp_address_suburb = models.CharField(max_length=50, blank=True, null=True)
    client_emp_address_postal_code = models.CharField(
        max_length=50, blank=True, null=True
    )
    client_emp_address_country = models.CharField(max_length=50, blank=True, null=True)
    clientEmployeeSpecialInstruc = models.TextField(
        max_length=500, blank=True, null=True
    )
    clientEmployeeCommLateBookings = models.CharField(
        max_length=50, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created By Account"), max_length=25, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified By Account"), max_length=25, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )
    status_time = models.DateTimeField(
        verbose_name=_("Status Time"), default=datetime.now, blank=True
    )

    class Meta:
        db_table = "dme_client_employees"

    def get_role(self):
        role = DME_Roles.objects.get(id=self.role_id)
        return role.role_code


class Dme_manifest_log(models.Model):
    id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("FK Booking Id"), max_length=64, blank=True, null=True
    )
    manifest_number = models.CharField(max_length=32, blank=True, null=True)
    manifest_url = models.CharField(max_length=200, blank=True, null=True)
    is_one_booking = models.BooleanField(blank=True, null=True, default=False)
    bookings_cnt = models.IntegerField(default=0, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_manifest_log"


class RuleTypes(models.Model):
    id = models.AutoField(primary_key=True)
    rule_type_code = models.CharField(
        max_length=16, blank=True, null=True, default=None,
    )
    calc_type = models.CharField(max_length=128, blank=True, null=True, default=None,)
    charge_rule = models.CharField(max_length=255, blank=True, null=True, default=None,)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "rule_types"


class Fp_freight_providers(models.Model):
    id = models.AutoField(primary_key=True)
    fp_company_name = models.CharField(max_length=64, blank=True, null=True)
    fp_address_country = models.CharField(max_length=32, blank=True, null=True)
    fp_inactive_date = models.DateField(blank=True, null=True)
    fp_manifest_cnt = models.IntegerField(default=1, blank=True, null=True)
    new_connot_index = models.IntegerField(default=1, blank=True, null=True)
    fp_markupfuel_levy_percent = models.FloatField(default=0, blank=True, null=True)
    prices_count = models.IntegerField(default=1, blank=True, null=True)
    service_cutoff_time = models.TimeField(default=None, blank=True, null=True)
    rule_type = models.ForeignKey(RuleTypes, on_delete=models.CASCADE, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "fp_freight_providers"


class DME_Service_Codes(models.Model):
    id = models.AutoField(primary_key=True)
    service_code = models.CharField(max_length=32, blank=True, null=True, default=None)
    service_name = models.CharField(max_length=32, blank=True, null=True, default=None)
    description = models.CharField(max_length=128, blank=True, null=True, default=None)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_service_codes"


class FP_Service_ETDs(models.Model):
    id = models.AutoField(primary_key=True)
    freight_provider = models.ForeignKey(Fp_freight_providers, on_delete=models.CASCADE)
    dme_service_code = models.ForeignKey(DME_Service_Codes, on_delete=models.CASCADE)
    fp_delivery_service_code = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    fp_delivery_time_description = models.TextField(
        max_length=512, blank=True, null=True, default=None
    )
    fp_service_time_uom = models.CharField(
        max_length=16, blank=True, null=True, default=None
    )
    fp_03_delivery_hours = models.FloatField(blank=True, null=True, default=None)
    service_cutoff_time = models.TimeField(default=None, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "fp_service_etds"


class API_booking_quotes(models.Model):
    id = models.AutoField(primary_key=True)
    api_results_id = models.CharField(
        verbose_name=_("Result ID"), blank=True, null=True, max_length=128
    )
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    fk_client_id = models.CharField(
        verbose_name=_("Client ID"), max_length=64, blank=True, null=True
    )
    fk_freight_provider_id = models.CharField(
        verbose_name=_("Freight Provider ID"), max_length=64, blank=True, null=True
    )
    account_code = models.CharField(
        verbose_name=_("Account Code"), max_length=32, blank=True, null=True
    )
    provider = models.CharField(
        verbose_name=_("Provider"), max_length=64, blank=True, null=True
    )
    service_code = models.CharField(
        verbose_name=_("Service Code"), max_length=10, blank=True, null=True
    )
    service_name = models.CharField(
        verbose_name=_("Service Name"), max_length=64, blank=True, null=True
    )
    fee = models.FloatField(verbose_name=_("Fee"), blank=True, null=True)
    etd = models.CharField(verbose_name=_("ETD"), max_length=64, blank=True, null=True)
    tax_id_1 = models.CharField(
        verbose_name=_("Tax ID 1"), max_length=10, blank=True, null=True
    )
    tax_value_1 = models.FloatField(
        verbose_name=_("Tax Value 1"), blank=True, null=True
    )
    tax_id_2 = models.CharField(
        verbose_name=_("Tax ID 2"), max_length=10, blank=True, null=True
    )
    tax_value_2 = models.FloatField(
        verbose_name=_("Tax Value 2"), blank=True, null=True
    )
    tax_id_3 = models.CharField(
        verbose_name=_("Tax ID 3"), max_length=10, blank=True, null=True
    )
    tax_value_3 = models.FloatField(
        verbose_name=_("Tax Value 3"), blank=True, null=True
    )
    tax_id_4 = models.CharField(
        verbose_name=_("Tax ID 4"), max_length=10, blank=True, null=True
    )
    tax_value_4 = models.FloatField(
        verbose_name=_("Tax Value 4"), blank=True, null=True
    )
    tax_id_5 = models.CharField(
        verbose_name=_("Tax ID 5"), max_length=10, blank=True, null=True
    )
    tax_value_5 = models.FloatField(
        verbose_name=_("Tax Value 5"), blank=True, null=True
    )
    b_client_markup2_percentage = models.FloatField(
        verbose_name=_("Client Markup2 Percent"), blank=True, null=True
    )
    fp_01_pu_possible = models.CharField(
        verbose_name=_("PU possible"), max_length=64, blank=True, null=True
    )
    fp_02_del_possible = models.CharField(
        verbose_name=_("DEL possible"), max_length=64, blank=True, null=True
    )
    fp_03_del_possible_price = models.CharField(
        verbose_name=_("DEL possible price"), max_length=64, blank=True, null=True
    )
    booking_cut_off = models.DateTimeField(
        verbose_name=_("Booking cut off"), default=datetime.now, blank=True, null=True
    )
    collection_cut_off = models.DateTimeField(
        verbose_name=_("Collection cut off"),
        default=datetime.now,
        blank=True,
        null=True,
    )
    mu_percentage_fuel_levy = models.FloatField(
        verbose_name=_("Mu Percentage Fuel Levy"), blank=True, null=True
    )
    client_mu_1_minimum_values = models.FloatField(
        verbose_name=_("Client MU 1 Minimum Value"), blank=True, null=True
    )
    x_price_per_UOM = models.IntegerField(
        verbose_name=_("Price per UOM"), blank=True, null=True
    )
    fp_latest_promised_pu = models.DateTimeField(
        verbose_name=_("Lastest Promised PU"),
        default=datetime.now,
        blank=True,
        null=True,
    )
    fp_latest_promised_del = models.DateTimeField(
        verbose_name=_("Lastest Timestamp DEL"),
        default=datetime.now,
        blank=True,
        null=True,
    )
    x_for_dme_price_ToxbyPricePerUOM = models.IntegerField(
        verbose_name=_("For DME Price ToxByPricePerUOM"), blank=True, null=True
    )
    x_for_dem_price_base_price = models.IntegerField(
        verbose_name=_("For DEM Price Base Price"), blank=True, null=True
    )
    x_fk_pricin_id = models.IntegerField(
        verbose_name=_("Pricin ID"), blank=True, null=True
    )
    x_price_surcharge = models.IntegerField(
        verbose_name=_("Price Surcharge"), blank=True, null=True
    )
    x_minumum_charge = models.IntegerField(
        verbose_name=_("Minimum Charge"), blank=True, null=True
    )
    z_fp_delivery_hours = models.IntegerField(
        verbose_name=_("Delivery Hours"), blank=True, null=True
    )
    s_05_LatestPickUpDateTimeFinal = models.DateTimeField(
        verbose_name=_("Latest PickUP Date Time Final"),
        default=datetime.now,
        blank=True,
        null=True,
    )
    s_06_LatestDeliveryDateTimeFinal = models.DateTimeField(
        verbose_name=_("Latest Delivery Date Time Final"),
        default=datetime.now,
        blank=True,
        null=True,
    )
    z_03_selected_lowest_priced_FC_that_passed = models.FloatField(
        verbose_name=_("Selected Lowest Priced FC That Passed"), blank=True, null=True
    )
    zc_dme_service_translation_nocalc = models.CharField(
        verbose_name=_("DME service translation no calc"),
        max_length=64,
        blank=True,
        null=True,
    )
    z_selected_manual_auto = models.CharField(
        verbose_name=_("Selected Manual Auto"), max_length=64, blank=True, null=True
    )
    z_selected_timestamp = models.DateTimeField(
        verbose_name=_("Selected Timestamp"), default=datetime.now
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "api_booking_quotes"


class Bookings(models.Model):
    id = models.AutoField(primary_key=True)
    b_bookingID_Visual = models.IntegerField(
        verbose_name=_("BookingID Visual"), blank=True, null=True, default=0
    )
    b_dateBookedDate = models.DateTimeField(
        verbose_name=_("Booked Date"), blank=True, null=True
    )
    puPickUpAvailFrom_Date = models.DateField(
        verbose_name=_("PickUp Available From"), blank=True, null=True
    )
    b_clientReference_RA_Numbers = models.CharField(
        verbose_name=_("Client Reference Ra Numbers"),
        max_length=1000,
        blank=True,
        null=True,
        default="",
    )
    b_status = models.CharField(
        verbose_name=_("Status"), max_length=40, blank=True, null=True, default=""
    )
    vx_freight_provider = models.CharField(
        verbose_name=_("Freight Provider"),
        max_length=100,
        blank=True,
        null=True,
        default="",
    )
    vx_serviceName = models.CharField(
        verbose_name=_("Service Name"), max_length=50, blank=True, null=True, default=""
    )
    s_05_LatestPickUpDateTimeFinal = models.DateTimeField(
        verbose_name=_("Lastest PickUp DateTime"), blank=True, null=True
    )
    s_06_LatestDeliveryDateTimeFinal = models.DateTimeField(
        verbose_name=_("Latest Delivery DateTime"), blank=True, null=True
    )
    v_FPBookingNumber = models.CharField(
        verbose_name=_("FP Booking Number"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    puCompany = models.CharField(
        verbose_name=_("Company"), max_length=128, blank=True, null=True, default=""
    )
    deToCompanyName = models.CharField(
        verbose_name=_("Company Name"),
        max_length=128,
        blank=True,
        null=True,
        default="",
    )
    consignment_label_link = models.CharField(
        verbose_name=_("Consignment"), max_length=250, blank=True, null=True, default=""
    )
    error_details = models.CharField(
        verbose_name=_("Error Detail"),
        max_length=250,
        blank=True,
        null=True,
        default="",
    )
    fk_client_warehouse = models.ForeignKey(
        Client_warehouses, on_delete=models.CASCADE, default="1"
    )
    b_clientPU_Warehouse = models.CharField(
        verbose_name=_("warehouse"), max_length=32, blank=True, null=True
    )
    is_printed = models.BooleanField(
        verbose_name=_("Is printed"), default=False, blank=True, null=True
    )
    shipping_label_base64 = models.CharField(
        verbose_name=_("Based64 Label"),
        max_length=255,
        blank=True,
        null=True,
        default="",
    )
    kf_client_id = models.CharField(
        verbose_name=_("KF Client ID"), max_length=64, blank=True, null=True, default=""
    )
    b_client_name = models.CharField(
        verbose_name=_("Client Name"), max_length=36, blank=True, null=True, default=""
    )
    pk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True, default=""
    )
    zb_002_client_booking_key = models.CharField(
        verbose_name=_("Client Booking Key"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    fk_fp_pickup_id = models.CharField(
        verbose_name=_("KF FP pickup id"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    pu_pickup_instructions_address = models.TextField(
        verbose_name=_("Pickup instrunctions address"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    kf_staff_id = models.CharField(
        verbose_name=_("Staff ID"), max_length=64, blank=True, null=True, default=""
    )
    kf_clientCustomerID_PU = models.CharField(
        verbose_name=_("Custom ID Pick Up"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_clientCustomerID_DE = models.CharField(
        verbose_name=_("Custom ID Deliver"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_Add_ID_PU = models.CharField(
        verbose_name=_("Add ID Pick Up"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_Add_ID_DE = models.CharField(
        verbose_name=_("Add ID Deliver"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_FP_ID = models.CharField(
        verbose_name=_("FP ID"), max_length=64, blank=True, null=True, default=""
    )
    kf_booking_Created_For_ID = models.CharField(
        verbose_name=_("Booking Created For ID"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_email_Template = models.CharField(
        verbose_name=_("Email Template"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    inv_dme_invoice_no = models.CharField(
        verbose_name=_("Invoice Num Booking"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_booking_quote_import_id = models.CharField(
        verbose_name=_("Booking Quote Import ID"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    kf_order_id = models.CharField(
        verbose_name=_("Order ID"), max_length=64, blank=True, null=True, default=""
    )
    x_Data_Entered_Via = models.CharField(
        verbose_name=_("Data Entered Via"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    b_booking_Priority = models.CharField(
        verbose_name=_("Booking Priority"),
        max_length=32,
        blank=True,
        null=True,
        default="",
    )
    z_API_Issue = models.IntegerField(
        verbose_name=_("Api Issue"), blank=True, null=True, default=0
    )
    z_api_issue_update_flag_500 = models.BooleanField(
        verbose_name=_("API Issue Update Flag 500"),
        default=False,
        blank=True,
        null=True,
    )
    pu_Address_Type = models.CharField(
        verbose_name=_("PU Address Type"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_Street_1 = models.CharField(
        verbose_name=_("PU Address Street 1"),
        max_length=80,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_street_2 = models.CharField(
        verbose_name=_("PU Address Street 2"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_State = models.CharField(
        verbose_name=_("PU Address State"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_City = models.CharField(
        verbose_name=_("PU Address City"),
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_Suburb = models.CharField(
        verbose_name=_("PU Address Suburb"),
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_PostalCode = models.CharField(
        verbose_name=_("PU Address Postal Code"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Address_Country = models.CharField(
        verbose_name=_("PU Address Country"),
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    pu_Contact_F_L_Name = models.CharField(
        verbose_name=_("PU Contact Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Phone_Main = models.CharField(
        verbose_name=_("PU Phone Main"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Phone_Mobile = models.CharField(
        verbose_name=_("PU Phone Mobile"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Email = models.CharField(
        verbose_name=_("PU Email"), max_length=64, blank=True, null=True, default=""
    )
    pu_email_Group_Name = models.CharField(
        verbose_name=_("PU Email Group Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_email_Group = models.TextField(
        verbose_name=_("PU Email Group"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    pu_Comm_Booking_Communicate_Via = models.CharField(
        verbose_name=_("PU Booking Communicate Via"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_Contact_FName = models.CharField(
        verbose_name=_("PU Contact First Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    pu_PickUp_Instructions_Contact = models.TextField(
        verbose_name=_("PU Instructions Contact"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    pu_WareHouse_Number = models.CharField(
        verbose_name=_("PU Warehouse Number"),
        max_length=10,
        blank=True,
        null=True,
        default="",
    )
    pu_WareHouse_Bay = models.CharField(
        verbose_name=_("PU Warehouse Bay"),
        max_length=10,
        blank=True,
        null=True,
        default="",
    )
    pu_Contact_Lname = models.CharField(
        verbose_name=_("PU Contact Last Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    de_Email = models.CharField(
        verbose_name=_("DE Email"), max_length=64, blank=True, null=True, default=""
    )
    de_To_AddressType = models.CharField(
        verbose_name=_("DE Address Type"),
        max_length=20,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_Street_1 = models.CharField(
        verbose_name=_("DE Address Street 1"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_Street_2 = models.CharField(
        verbose_name=_("DE Address Street 2"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_State = models.CharField(
        verbose_name=_("DE Address State"),
        max_length=20,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_City = models.CharField(
        verbose_name=_("DE Address City"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_Suburb = models.CharField(
        verbose_name=_("DE Address Suburb"),
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_PostalCode = models.CharField(
        verbose_name=_("DE Address Postal Code"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    de_To_Address_Country = models.CharField(
        verbose_name=_("DE Address Country"),
        max_length=12,
        blank=True,
        null=True,
        default="",
    )
    de_to_Contact_F_LName = models.CharField(
        verbose_name=_("DE Contact Name"),
        max_length=50,
        blank=True,
        null=True,
        default="",
    )
    de_to_Contact_FName = models.CharField(
        verbose_name=_("DE Contact First Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    de_to_Contact_Lname = models.CharField(
        verbose_name=_("DE Contact Last Name"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    de_To_Comm_Delivery_Communicate_Via = models.CharField(
        verbose_name=_("DE Communicate Via"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )
    de_to_Pick_Up_Instructions_Contact = models.TextField(
        verbose_name=_("DE Instructions Contact"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    de_to_PickUp_Instructions_Address = models.TextField(
        verbose_name=_("DE Instructions Address"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    de_to_WareHouse_Number = models.CharField(
        verbose_name=_("DE Warehouse Number"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    de_to_WareHouse_Bay = models.CharField(
        verbose_name=_("DE Warehouse Bay"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    de_to_Phone_Mobile = models.CharField(
        verbose_name=_("DE Phone Mobile"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    de_to_Phone_Main = models.CharField(
        verbose_name=_("DE Phone Main"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    de_to_addressed_Saved = models.IntegerField(
        verbose_name=_("DE Addressed Saved"), blank=True, default=0, null=True
    )
    de_Contact = models.CharField(
        verbose_name=_("DE Contact"), max_length=50, blank=True, null=True, default=""
    )
    pu_PickUp_By_Date = models.DateField(
        verbose_name=_("PickUp By Date"), blank=True, null=True
    )
    pu_addressed_Saved = models.IntegerField(
        verbose_name=_("PU Addressed Saved"), blank=True, null=True, default=0
    )
    b_date_booked_by_dme = models.DateField(
        verbose_name=_("Date Booked By DME"), blank=True, null=True
    )
    b_booking_Notes = models.TextField(
        verbose_name=_("Booking Notes"),
        max_length=400,
        blank=True,
        null=True,
        default="",
    )
    s_02_Booking_Cutoff_Time = models.TimeField(
        verbose_name=_("Booking Cutoff Time"), blank=True, null=True
    )
    s_05_Latest_PickUp_Date_Time_Override = models.DateTimeField(
        verbose_name=_("Latest PU DateTime Override"), blank=True, null=True
    )
    s_05_Latest_Pick_Up_Date_TimeSet = models.DateTimeField(
        verbose_name=_("Latest PU DateTime Set"), blank=True, null=True
    )
    s_06_Latest_Delivery_Date_Time_Override = models.DateTimeField(
        verbose_name=_("Latest DE DateTime Override"), blank=True, null=True
    )
    s_06_Latest_Delivery_Date_TimeSet = models.DateTimeField(
        verbose_name=_("Latest DE DateTime Set"), blank=True, null=True
    )
    s_07_PickUp_Progress = models.CharField(
        verbose_name=_("PU Progress"), max_length=30, blank=True, null=True, default=""
    )
    s_08_Delivery_Progress = models.CharField(
        verbose_name=_("DE Progress"), max_length=30, blank=True, null=True, default=""
    )
    s_20_Actual_Pickup_TimeStamp = models.DateTimeField(
        verbose_name=_("Actual PU TimeStamp"), blank=True, null=True
    )
    s_21_Actual_Delivery_TimeStamp = models.DateTimeField(
        verbose_name=_("Actual DE TimeStamp"), blank=True, null=True
    )
    b_handling_Instructions = models.TextField(
        verbose_name=_("Handling Instructions"),
        max_length=120,
        blank=True,
        null=True,
        default="",
    )
    v_price_Booking = models.FloatField(
        verbose_name=_("Price Booking"), default=0, blank=True, null=True
    )
    v_service_Type_2 = models.CharField(
        verbose_name=_("Service Type 2"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    b_status_API = models.CharField(
        verbose_name=_("Status API"), max_length=255, blank=True, null=True, default=""
    )
    v_vehicle_Type = models.CharField(
        verbose_name=_("Vehicle Type"), max_length=30, blank=True, null=True, default=""
    )
    v_customer_code = models.CharField(
        verbose_name=_("Customer Code"),
        max_length=20,
        blank=True,
        null=True,
        default="",
    )
    v_service_Type_ID = models.CharField(
        verbose_name=_("Service Type ID"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    v_service_Type = models.CharField(
        verbose_name=_("Service Type"), max_length=25, blank=True, null=True, default=""
    )
    v_serviceCode_DME = models.CharField(
        verbose_name=_("Service Code DME"),
        max_length=10,
        blank=True,
        null=True,
        default="",
    )
    v_service_Delivery_Days_Percentage_Days_TO_PU = models.FloatField(
        verbose_name=_("Service DE days Percentage Days To PU"),
        default=0,
        blank=True,
        null=True,
    )
    v_serviceTime_End = models.TimeField(
        verbose_name=_("Service Time End"), blank=True, null=True
    )
    v_serviceTime_Start = models.TimeField(
        verbose_name=_("Service Time Start"), blank=True, null=True
    )
    v_serviceDelivery_Days = models.IntegerField(
        verbose_name=_("Service DE Days"), blank=True, default=0, null=True
    )
    v_service_Delivery_Hours = models.IntegerField(
        verbose_name=_("Service DE Hours"), blank=True, default=0, null=True
    )
    v_service_DeliveryHours_TO_PU = models.IntegerField(
        verbose_name=_("Service DE Hours To PU"), blank=True, default=0, null=True
    )
    x_booking_Created_With = models.CharField(
        verbose_name=_("Booking Created With"), max_length=32, blank=True, null=True,
    )
    x_manual_booked_flag = models.BooleanField(default=False, blank=True, null=True)
    de_Email_Group_Emails = models.TextField(
        verbose_name=_("DE Email Group Emails"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )
    de_Email_Group_Name = models.CharField(
        verbose_name=_("DE Email Group Name"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    de_Options = models.CharField(
        verbose_name=_("DE Options"), max_length=30, blank=True, null=True, default=""
    )
    total_lines_qty_override = models.FloatField(
        verbose_name=_("Total Lines Qty Override"), blank=True, default=0, null=True
    )
    total_1_KG_weight_override = models.FloatField(
        verbose_name=_("Total 1Kg Weight Override"), default=0, blank=True, null=True
    )
    total_Cubic_Meter_override = models.FloatField(
        verbose_name=_("Total Cubic Meter Override"), default=0, blank=True, null=True
    )
    booked_for_comm_communicate_via = models.CharField(
        verbose_name=_("Booked Communicate Via"),
        max_length=120,
        blank=True,
        null=True,
        default="",
    )
    booking_Created_For = models.CharField(
        verbose_name=_("Booking Created For"),
        max_length=20,
        blank=True,
        null=True,
        default="",
    )
    b_order_created = models.CharField(
        verbose_name=_("Order Created"),
        max_length=45,
        blank=True,
        null=True,
        default="",
    )
    b_error_Capture = models.TextField(
        verbose_name=_("Error Capture"),
        max_length=1000,
        blank=True,
        null=True,
        default="",
    )
    b_error_code = models.CharField(
        verbose_name=_("Error Code"), max_length=20, blank=True, null=True, default=""
    )
    b_booking_Category = models.CharField(
        verbose_name=_("Booking Categroy"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    pu_PickUp_By_Time_Hours = models.IntegerField(
        verbose_name=_("PU By Time Hours"), blank=True, default=0, null=True
    )
    pu_PickUp_By_Time_Minutes = models.IntegerField(
        verbose_name=_("PU By Time Minutes"), blank=True, default=0, null=True
    )
    pu_PickUp_Avail_Time_Hours = models.IntegerField(
        verbose_name=_("PU Available Time Hours"), blank=True, default=0, null=True
    )
    pu_PickUp_Avail_Time_Minutes = models.IntegerField(
        verbose_name=_("PU Available Time Minutes"), blank=True, default=0, null=True
    )
    pu_PickUp_Avail_From_Date_DME = models.DateField(
        verbose_name=_("PU Available From Date DME"), blank=True, null=True
    )
    pu_PickUp_Avail_Time_Hours_DME = models.IntegerField(
        verbose_name=_("PU Available Time Hours DME"), blank=True, default=0, null=True
    )
    pu_PickUp_Avail_Time_Minutes_DME = models.IntegerField(
        verbose_name=_("PU Available Time Minutes DME"),
        blank=True,
        default=0,
        null=True,
    )
    pu_PickUp_By_Date_DME = models.DateField(
        verbose_name=_("PU By Date DME"), blank=True, null=True
    )
    pu_PickUp_By_Time_Hours_DME = models.IntegerField(
        verbose_name=_("PU By Time Hours DME"), blank=True, default=0, null=True
    )
    pu_PickUp_By_Time_Minutes_DME = models.IntegerField(
        verbose_name=_("PU By Time Minutes DME"), blank=True, default=0, null=True
    )
    pu_Actual_Date = models.DateField(
        verbose_name=_("PU Actual Date"), blank=True, null=True
    )
    pu_Actual_PickUp_Time = models.TimeField(
        verbose_name=_("Actual PU Time"), blank=True, null=True
    )
    de_Deliver_From_Date = models.DateField(
        verbose_name=_("DE From Date"), blank=True, null=True
    )
    de_Deliver_From_Hours = models.IntegerField(
        verbose_name=_("DE From Hours"), blank=True, default=0, null=True
    )
    de_Deliver_From_Minutes = models.IntegerField(
        verbose_name=_("DE From Minutes"), blank=True, default=0, null=True
    )
    de_Deliver_By_Date = models.DateField(
        verbose_name=_("DE By Date"), blank=True, null=True
    )
    de_Deliver_By_Hours = models.IntegerField(
        verbose_name=_("DE By Hours"), blank=True, default=0, null=True
    )
    de_Deliver_By_Minutes = models.IntegerField(
        verbose_name=_("De By Minutes"), blank=True, default=0, null=True
    )
    DME_Base_Cost = models.FloatField(
        verbose_name=_("DME Base Cost"), default=0, blank=True, null=True
    )
    vx_Transit_Duration = models.IntegerField(
        verbose_name=_("Transit Duration"), blank=True, default=0, null=True
    )
    vx_freight_time = models.DateTimeField(
        verbose_name=_("Freight Time"), blank=True, null=True
    )
    vx_price_Booking = models.FloatField(
        verbose_name=_("VX Price Booking"), default=0, blank=True, null=True
    )
    vx_price_Tax = models.FloatField(
        verbose_name=_("VX Price Tax"), default=0, blank=True, null=True
    )
    vx_price_Total_Sell_Price_Override = models.FloatField(
        verbose_name=_("VX Price Total Sell Price Override"),
        default=0,
        blank=True,
        null=True,
    )
    vx_fp_pu_eta_time = models.DateTimeField(
        verbose_name=_("FP PickUp ETA Time"), blank=True, null=True
    )
    vx_fp_del_eta_time = models.DateTimeField(
        verbose_name=_("FP Delivery ETA Time"), blank=True, null=True
    )
    vx_service_Name_ID = models.CharField(
        verbose_name=_("Service Name ID"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    vx_futile_Booking_Notes = models.CharField(
        verbose_name=_("Futile Booking Notes"),
        max_length=200,
        blank=True,
        null=True,
        default="",
    )
    z_CreatedByAccount = models.TextField(
        verbose_name=_("Created By Account"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    pu_Operting_Hours = models.TextField(
        verbose_name=_("PU Operating hours"),
        max_length=500,
        blank=True,
        null=True,
        default="",
    )
    de_Operating_Hours = models.TextField(
        verbose_name=_("DE Operating hours"),
        max_length=500,
        blank=True,
        null=True,
        default="",
    )
    z_CreatedTimestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    z_ModifiedByAccount = models.CharField(
        verbose_name=_("Modified By Account"), max_length=25, blank=True, null=True,
    )
    z_ModifiedTimestamp = models.DateTimeField(auto_now=True, null=True, blank=True)
    pu_PickUp_TimeSlot_TimeEnd = models.TimeField(
        verbose_name=_("PU TimeSlot TimeEnd"), blank=True, null=True
    )
    de_TimeSlot_TimeStart = models.TimeField(
        verbose_name=_("DE TimeSlot TimeStart"), blank=True, null=True
    )
    de_TimeSlot_Time_End = models.TimeField(
        verbose_name=_("TimeSlot Time End"), blank=True, null=True
    )
    de_Nospecific_Time = models.IntegerField(
        verbose_name=_("No Specific Time"), blank=True, default=0, null=True
    )
    de_to_TimeSlot_Date_End = models.DateField(
        verbose_name=_("DE to TimeSlot Date End"), blank=True, null=True
    )
    rec_do_not_Invoice = models.IntegerField(
        verbose_name=_("Rec Doc Not Invoice"), blank=True, default=0, null=True
    )
    b_email_Template_Name = models.CharField(
        verbose_name=_("Email Template Name"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    pu_No_specified_Time = models.IntegerField(
        verbose_name=_("PU No Specific Time"), blank=True, default=0, null=True
    )
    notes_cancel_Booking = models.CharField(
        verbose_name=_("Notes Cancel Booking"),
        max_length=500,
        blank=True,
        null=True,
        default="",
    )
    booking_Created_For_Email = models.CharField(
        verbose_name=_("Booking Created For Email"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    z_Notes_Bugs = models.CharField(
        verbose_name=_("Notes Bugs"), max_length=200, blank=True, null=True, default=""
    )
    DME_GST_Percentage = models.IntegerField(
        verbose_name=_("DME GST Percentage"), blank=True, default=0, null=True
    )
    x_ReadyStatus = models.CharField(
        verbose_name=_("Ready Status"), max_length=32, blank=True, null=True, default=""
    )
    DME_Notes = models.CharField(
        verbose_name=_("DME Notes"), max_length=500, blank=True, null=True, default=""
    )
    b_client_Reference_RA_Numbers_lastupdate = models.DateTimeField(
        verbose_name=_("Client Reference RA Number Last Update"), blank=True, null=True
    )
    s_04_Max_Duration_To_Delivery_Number = models.IntegerField(
        verbose_name=_("04 Max Duration To Delivery Number"),
        blank=True,
        default=0,
        null=True,
    )
    b_client_MarkUp_PercentageOverRide = models.FloatField(
        verbose_name=_("Client MarkUp Percentage Override"),
        default=0,
        blank=True,
        null=True,
    )
    z_admin_dme_invoice_number = models.CharField(
        verbose_name=_("Admin DME Invoice Number"),
        max_length=25,
        blank=True,
        null=True,
        default="",
    )
    z_included_with_manifest_date = models.DateTimeField(
        verbose_name=_("Included With Manifest Date"), blank=True, null=True
    )
    b_dateinvoice = models.DateField(
        verbose_name=_("Date Invoice"), blank=True, null=True
    )
    b_booking_tail_lift_pickup = models.BooleanField(
        verbose_name=_("Booking Tail Lift PU"), default=False, blank=True, null=True
    )
    b_booking_tail_lift_deliver = models.BooleanField(
        verbose_name=_("Booking Tail Lift DE"), default=False, blank=True, null=True
    )
    b_booking_no_operator_pickup = models.PositiveIntegerField(
        verbose_name=_("Booking No Operator PU"), blank=True, default=None, null=True
    )
    b_bookingNoOperatorDeliver = models.PositiveIntegerField(
        verbose_name=_("Booking No Operator DE"), blank=True, default=None, null=True
    )
    b_ImportedFromFile = models.CharField(
        verbose_name=_("Imported File Filed"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    b_email2_return_sent_numberofTimes = models.IntegerField(
        verbose_name=_("Email2 Return Sent Number Of Times"),
        blank=True,
        default=0,
        null=True,
    )
    b_email1_general_sent_Number_of_times = models.IntegerField(
        verbose_name=_("Email1 General sent Number Of Times"),
        blank=True,
        default=0,
        null=True,
    )
    b_email3_pickup_sent_numberOfTimes = models.IntegerField(
        verbose_name=_("Email3 PU Sent Number Of Times"),
        blank=True,
        default=0,
        null=True,
    )
    b_email4_futile_sent_number_of_times = models.IntegerField(
        verbose_name=_("Email4 Futile Sent Number Of Times"),
        blank=True,
        default=0,
        null=True,
    )
    b_send_POD_eMail = models.BooleanField(default=False, null=True, blank=True)
    b_booking_status_manual = models.CharField(
        verbose_name=_("Booking Status Manual"),
        max_length=30,
        blank=True,
        null=True,
        default="",
    )
    b_booking_status_manual_DME = models.CharField(
        verbose_name=_("Booking Status Manual DME"),
        max_length=2,
        blank=True,
        null=True,
        default="",
    )
    b_booking_statusmanual_DME_Note = models.CharField(
        verbose_name=_("Booking Status Manual DME Note"),
        max_length=200,
        blank=True,
        null=True,
        default="",
    )
    DME_price_from_client = models.IntegerField(
        verbose_name=_("DME Price From Client"), blank=True, default=0, null=True
    )
    z_label_url = models.CharField(
        verbose_name=_("PDF Url"), max_length=255, blank=True, null=True, default=""
    )
    z_lastStatusAPI_ProcessedTimeStamp = models.DateTimeField(
        verbose_name=_("Last StatusAPI Processed Timestamp"), blank=True, null=True
    )
    s_21_ActualDeliveryTimeStamp = models.DateTimeField(
        verbose_name=_("Actual Delivery Timestamp"), blank=True, null=True
    )
    b_client_booking_ref_num = models.CharField(
        verbose_name=_("Booking Ref Num"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    b_client_sales_inv_num = models.CharField(
        verbose_name=_("Sales Inv Num"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    b_client_order_num = models.CharField(
        verbose_name=_("Order Num"), max_length=64, blank=True, null=True, default=""
    )
    b_client_del_note_num = models.CharField(
        verbose_name=_("Del Note Num"), max_length=64, blank=True, null=True, default=""
    )
    b_client_warehouse_code = models.CharField(
        verbose_name=_("Warehouse code"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    z_downloaded_shipping_label_timestamp = models.DateTimeField(
        verbose_name=_("downloaded_shipping_label_timestamp"), blank=True, null=True
    )
    vx_fp_order_id = models.CharField(
        verbose_name=_("Order ID"), max_length=64, blank=True, null=True, default=""
    )
    z_manifest_url = models.CharField(
        verbose_name=_("Manifest URL"),
        max_length=128,
        blank=True,
        null=True,
        default="",
    )
    z_pod_url = models.CharField(max_length=255, blank=True, null=True, default="")
    z_pod_signed_url = models.CharField(
        max_length=255, blank=True, null=True, default=""
    )
    z_connote_url = models.CharField(max_length=255, blank=True, null=True, default="")
    z_downloaded_pod_timestamp = models.DateTimeField(blank=True, null=True)
    z_downloaded_pod_sog_timestamp = models.DateTimeField(blank=True, null=True)
    z_downloaded_connote_timestamp = models.DateTimeField(blank=True, null=True)
    booking_api_start_TimeStamp = models.DateTimeField(blank=True, null=True)
    booking_api_end_TimeStamp = models.DateTimeField(blank=True, null=True)
    booking_api_try_count = models.IntegerField(blank=True, default=0, null=True)
    z_manual_booking_set_to_confirm = models.DateTimeField(blank=True, null=True)
    z_manual_booking_set_time_push_to_fm = models.DateTimeField(blank=True, null=True)
    z_lock_status = models.BooleanField(default=False, blank=True, null=True)
    z_locked_status_time = models.DateTimeField(blank=True, null=True)
    delivery_kpi_days = models.IntegerField(blank=True, default=0, null=True)
    delivery_days_from_booked = models.IntegerField(blank=True, default=0, null=True)
    delivery_actual_kpi_days = models.IntegerField(blank=True, default=0, null=True)
    b_status_sub_client = models.CharField(
        max_length=50, blank=True, null=True, default=""
    )
    b_status_sub_fp = models.CharField(max_length=50, blank=True, null=True, default="")
    fp_store_event_date = models.DateField(blank=True, null=True)
    fp_store_event_time = models.TimeField(blank=True, null=True)
    fp_store_event_desc = models.CharField(
        max_length=255, blank=True, null=True, default=None
    )
    e_qty_scanned_fp_total = models.IntegerField(blank=True, null=True, default=0)
    dme_status_detail = models.CharField(
        max_length=100, blank=True, null=True, default=""
    )
    dme_status_action = models.CharField(
        max_length=100, blank=True, null=True, default=""
    )
    dme_status_linked_reference_from_fp = models.TextField(
        max_length=150, blank=True, null=True, default=""
    )
    rpt_pod_from_file_time = models.DateTimeField(blank=True, null=True)
    rpt_proof_of_del_from_csv_time = models.DateTimeField(blank=True, null=True)
    z_status_process_notes = models.TextField(
        max_length=1000, blank=True, null=True, default=""
    )
    tally_delivered = models.IntegerField(blank=True, default=0, null=True)
    manifest_timestamp = models.DateTimeField(blank=True, null=True)
    inv_billing_status = models.CharField(
        max_length=32, blank=True, null=True, default=""
    )
    inv_billing_status_note = models.CharField(
        max_length=255, blank=True, null=True, default=""
    )
    check_pod = models.BooleanField(default=False, blank=True, null=True)
    vx_freight_provider_carrier = models.CharField(
        max_length=32, blank=True, null=True, default=None
    )
    fk_manifest = models.ForeignKey(
        Dme_manifest_log, on_delete=models.CASCADE, default=None, null=True
    )
    b_is_flagged_add_on_services = models.BooleanField(
        default=False, blank=True, null=True
    )
    z_calculated_ETA = models.DateField(blank=True, null=True)
    b_client_name_sub = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    fp_invoice_no = models.CharField(max_length=16, blank=True, null=True, default=None)
    inv_cost_quoted = models.FloatField(blank=True, default=0, null=True)
    inv_cost_actual = models.FloatField(blank=True, default=0, null=True)
    inv_sell_quoted = models.FloatField(blank=True, default=0, null=True)
    inv_sell_quoted_override = models.FloatField(blank=True, default=None, null=True)
    inv_sell_actual = models.FloatField(blank=True, default=0, null=True)
    b_del_to_signed_name = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    b_del_to_signed_time = models.DateTimeField(blank=True, null=True, default=None)
    z_pushed_to_fm = models.BooleanField(default=False, blank=True, null=True)
    b_fp_qty_delivered = models.IntegerField(blank=True, default=0, null=True)
    jobNumber = models.CharField(max_length=45, blank=True, null=True, default=None)
    jobDate = models.CharField(max_length=45, blank=True, null=True, default=None)
    vx_account_code = models.CharField(max_length=32, blank=True, null=True, default="")
    b_booking_project = models.CharField(
        max_length=250, blank=True, null=True, default=None
    )
    b_project_opened = models.DateTimeField(blank=True, null=True, default=None)
    b_project_inventory_due = models.DateTimeField(blank=True, null=True, default=None)
    b_project_wh_unpack = models.DateTimeField(blank=True, null=True, default=None)
    b_project_dd_receive_date = models.DateTimeField(
        blank=True, null=True, default=None
    )
    b_project_due_date = models.DateField(blank=True, null=True, default=None)
    b_given_to_transport_date_time = models.DateTimeField(
        blank=True, null=True, default=None
    )
    fp_received_date_time = models.DateTimeField(blank=True, null=True)
    api_booking_quote = models.OneToOneField(
        API_booking_quotes, on_delete=models.CASCADE, null=True
    )  # Optional
    prev_dme_status_detail = models.CharField(
        max_length=255, blank=True, null=True, default=""
    )
    dme_status_detail_updated_at = models.DateTimeField(blank=True, null=True)
    dme_status_detail_updated_by = models.CharField(
        max_length=64, blank=True, null=True, default=""
    )
    delivery_booking = models.DateField(default=None, blank=True, null=True)

    class Meta:
        db_table = "dme_bookings"

    def get_max_b_bookingID_Visual():
        max = Bookings.objects.all().aggregate(Max("b_bookingID_Visual"))[
            "b_bookingID_Visual__max"
        ]
        return int(max)

    @property
    def has_comms(self):
        comms_count = Dme_comm_and_task.objects.filter(
            fk_booking_id=self.pk_booking_id
        ).count()

        if comms_count == 0:
            return False
        else:
            return True

    def had_status(self, status):
        results = Dme_status_history.objects.filter(
            fk_booking_id=self.pk_booking_id, status_last__iexact=status
        )

        return True if results else False

    def get_status_histories(self, status=None):
        status_histories = []

        if status:
            status_histories = Dme_status_history.objects.filter(
                fk_booking_id=self.pk_booking_id, status_last__iexact=status
            )
        else:
            status_histories = Dme_status_history.objects.filter(
                fk_booking_id=self.pk_booking_id
            )

        return status_histories

    @property
    def business_group(self):
        customer_group_name = ""
        customer_groups = Dme_utl_client_customer_group.objects.all()

        for customer_group in customer_groups:
            if (
                customer_group
                and self.deToCompanyName
                and customer_group.name_lookup.lower() in self.deToCompanyName.lower()
            ):
                customer_group_name = customer_group.group_name

        return customer_group_name

    @property
    def dme_delivery_status_category(self):
        try:
            utl_dme_status = Utl_dme_status.objects.get(
                dme_delivery_status=self.b_status
            )
            return utl_dme_status.dme_delivery_status_category
        except Exception as e:
            # print('Exception: ', e)
            return ""

    def get_total_lines_qty(self):
        try:
            qty = 0
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=self.pk_booking_id
            )

            for booking_line in booking_lines:
                if booking_line.e_qty:
                    qty += int(booking_line.e_qty)

            return qty
        except Exception as e:
            # print('Exception: ', e)
            logger.info("#591 Error - ", str(e))
            return 0

    @property
    def client_item_references(self):
        try:
            client_item_references = []
            booking_lines = Booking_lines.objects.filter(
                fk_booking_id=self.pk_booking_id
            )

            for booking_line in booking_lines:
                if booking_line.client_item_reference is not None:
                    client_item_references.append(booking_line.client_item_reference)

            return ", ".join(client_item_references)
        except Exception as e:
            # print('Exception: ', e)
            return ""

    @property
    def clientRefNumbers(self):
        try:
            clientRefNumbers = []
            booking_lines_data = Booking_lines_data.objects.filter(
                fk_booking_id=self.pk_booking_id
            )

            for booking_line_data in booking_lines_data:
                if booking_line_data.clientRefNumber is not None:
                    clientRefNumbers.append(booking_line_data.clientRefNumber)

            return ", ".join(clientRefNumbers)
        except Exception as e:
            # print('Exception: ', e)
            return ""

    @property
    def gap_ras(self):
        try:
            gap_ras = []
            booking_lines_data = Booking_lines_data.objects.filter(
                fk_booking_id=self.pk_booking_id
            )

            for booking_line_data in booking_lines_data:
                if booking_line_data.gap_ra is not None:
                    gap_ras.append(booking_line_data.gap_ra)

            return ", ".join(gap_ras)
        except Exception as e:
            # print('Exception: ', e)
            return ""

    def get_etd(self):
        if self.api_booking_quote:
            if self.vx_freight_provider.lower() == "tnt":
                return round(float(self.api_booking_quote.etd)), "days"
            elif self.api_booking_quote:
                freight_provider = Fp_freight_providers.objects.get(
                    fp_company_name=self.vx_freight_provider
                )
                service_etd = FP_Service_ETDs.objects.filter(
                    freight_provider_id=freight_provider.id,
                    fp_delivery_time_description=self.api_booking_quote.etd,
                ).first()

                if service_etd is not None:
                    if service_etd.fp_service_time_uom.lower() == "days":
                        return service_etd.fp_03_delivery_hours / 24, "days"
                    elif service_etd.fp_service_time_uom.lower() == "hours":
                        return service_etd.fp_03_delivery_hours, "hours"

        return None, None


class Booking_lines(models.Model):
    pk_lines_id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("FK Booking Id"), max_length=64, blank=True, null=True
    )
    pk_booking_lines_id = models.CharField(max_length=64, blank=True, null=True)
    e_type_of_packaging = models.CharField(
        verbose_name=_("Type Of Packaging"), max_length=36, blank=True, null=True
    )
    e_item_type = models.CharField(
        verbose_name=_("Item Type"), max_length=64, blank=True, null=True
    )
    e_pallet_type = models.CharField(
        verbose_name=_("Pallet Type"), max_length=24, blank=True, null=True
    )
    e_item = models.CharField(
        verbose_name=_("Item"), max_length=56, blank=True, null=True
    )
    e_qty = models.IntegerField(verbose_name=_("Quantity"), blank=True, null=True)
    e_weightUOM = models.CharField(
        verbose_name=_("Weight UOM"), max_length=56, blank=True, null=True
    )
    e_weightPerEach = models.FloatField(
        verbose_name=_("Weight Per Each"), blank=True, null=True
    )
    e_dimUOM = models.CharField(
        verbose_name=_("Dim UOM"), max_length=10, blank=True, null=True
    )
    e_dimLength = models.FloatField(verbose_name=_("Dim Length"), blank=True, null=True)
    e_dimWidth = models.FloatField(verbose_name=_("Dim Width"), blank=True, null=True)
    e_dimHeight = models.FloatField(verbose_name=_("Dim Height"), blank=True, null=True)
    e_dangerousGoods = models.IntegerField(
        verbose_name=_("Dangerous Goods"), blank=True, null=True
    )
    e_insuranceValueEach = models.IntegerField(
        verbose_name=_("Insurance Value Each"), blank=True, null=True
    )
    discount_rate = models.IntegerField(
        verbose_name=_("Discount Rate"), blank=True, null=True
    )
    e_options1 = models.CharField(
        verbose_name=_("Option 1"), max_length=56, blank=True, null=True
    )
    e_options2 = models.CharField(
        verbose_name=_("Option 2"), max_length=56, blank=True, null=True
    )
    e_options3 = models.CharField(
        verbose_name=_("Option 3"), max_length=56, blank=True, null=True
    )
    e_options4 = models.CharField(
        verbose_name=_("Option 4"), max_length=56, blank=True, null=True
    )
    fk_service_id = models.CharField(
        verbose_name=_("Service ID"), max_length=64, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created By Account"), max_length=24, blank=True, null=True
    )
    z_documentUploadedUser = models.CharField(
        verbose_name=_("Document Uploaded User"), max_length=24, blank=True, null=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified By Account"), max_length=24, blank=True, null=True
    )
    e_spec_clientRMA_Number = models.TextField(
        verbose_name=_("Spec ClientRMA Number"), max_length=300, blank=True, null=True
    )
    e_spec_customerReferenceNo = models.TextField(
        verbose_name=_("Spec Customer Reference No"),
        max_length=200,
        blank=True,
        null=True,
    )
    taxable = models.BooleanField(
        verbose_name=_("Taxable"), default=False, blank=True, null=True
    )
    e_Total_KG_weight = models.FloatField(
        verbose_name=_("Total KG Weight"), blank=True, default=0, null=True
    )
    e_1_Total_dimCubicMeter = models.FloatField(
        verbose_name=_("Total Dim Cubic Meter"), blank=True, default=0, null=True
    )
    client_item_reference = models.CharField(
        max_length=64, blank=True, null=True, default=""
    )
    total_2_cubic_mass_factor_calc = models.FloatField(
        verbose_name=_("Cubic Mass Factor"), blank=True, default=0, null=True
    )
    e_qty_awaiting_inventory = models.IntegerField(blank=True, null=True, default=0)
    e_qty_collected = models.IntegerField(blank=True, null=True, default=0)
    e_qty_scanned_depot = models.IntegerField(blank=True, null=True, default=0)
    e_qty_delivered = models.IntegerField(blank=True, null=True, default=0)
    e_qty_adjusted_delivered = models.IntegerField(blank=True, null=True, default=0)
    e_qty_damaged = models.IntegerField(blank=True, null=True, default=0)
    e_qty_returned = models.IntegerField(blank=True, null=True, default=0)
    e_qty_shortages = models.IntegerField(blank=True, null=True, default=0)
    e_qty_scanned_fp = models.IntegerField(blank=True, null=True, default=0)
    z_pushed_to_fm = models.BooleanField(default=False, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    def booking(self):
        try:
            return Bookings.objects.get(pk_booking_id=self.fk_booking_id)
        except Exception as e:
            logger.info(f"#516 Error: {str(e)}")
            return None

    def get_is_scanned(self):
        try:
            api_bcl = Api_booking_confirmation_lines.objects.filter(
                fk_booking_line_id=self.pk_lines_id
            ).first()
            if api_bcl.tally is not 0:
                return True
            return False
        except Exception as e:
            # print('Exception: ', e)
            return False

    def gap_ras(self):
        try:
            _gap_ras = []
            booking_lines_data = Booking_lines_data.objects.filter(
                fk_booking_lines_id=self.pk_booking_lines_id
            )

            for booking_line_data in booking_lines_data:
                if booking_line_data.gap_ra is not None:
                    _gap_ras.append(booking_line_data.gap_ra)

            return ", ".join(_gap_ras)
        except Exception as e:
            return ""

    class Meta:
        db_table = "dme_booking_lines"


class Booking_lines_data(models.Model):
    pk_id_lines_data = models.AutoField(primary_key=True)
    fk_booking_lines_id = models.CharField(
        verbose_name=_("FK Booking Lines Id"),
        max_length=64,
        blank=True,
        null=True,
        default=None,
    )
    fk_booking_id = models.CharField(
        verbose_name=_("FK Booking Id"), max_length=64, blank=True, null=True
    )
    modelNumber = models.CharField(
        verbose_name=_("Model Number"), max_length=50, blank=True, null=True
    )
    itemDescription = models.TextField(
        verbose_name=_("Item Description"), max_length=200, blank=True, null=True
    )
    quantity = models.IntegerField(verbose_name=_("Quantity"), blank=True, null=True)
    itemFaultDescription = models.TextField(
        verbose_name=_("Item Description"), max_length=200, blank=True, null=True
    )
    insuranceValueEach = models.IntegerField(
        verbose_name=_("Insurance Value Each"), blank=True, null=True
    )
    gap_ra = models.TextField(
        verbose_name=_("Gap Ra"), max_length=300, blank=True, null=True
    )
    clientRefNumber = models.CharField(
        verbose_name=_("Client Ref Number"), max_length=50, blank=True, null=True
    )
    itemSerialNumbers = models.CharField(
        verbose_name=_("Item Serial Numbers"), max_length=100, blank=True, null=True
    )
    z_pushed_to_fm = models.BooleanField(default=False, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    def booking(self):
        try:
            return Bookings.objects.get(pk_booking_id=self.fk_booking_id)
        except Exception as e:
            logger.info(f"#516 Error: {str(e)}")
            return None

    def booking_line(self):
        try:
            return Booking_lines.objects.get(
                pk_booking_lines_id=self.fk_booking_lines_id
            )
        except Exception as e:
            logger.info(f"#516 Error: {str(e)}")
            return None

    class Meta:
        db_table = "dme_booking_lines_data"


class Dme_attachments(models.Model):
    pk_id_attachment = models.AutoField(primary_key=True)
    fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
    fk_id_dme_booking = models.CharField(
        verbose_name=_("FK Booking Id"), max_length=64, blank=True, null=True
    )
    fileName = models.CharField(verbose_name=_("filename"), max_length=230, blank=False)
    linkurl = models.CharField(
        verbose_name=_("linkurl"), max_length=430, blank=True, null=True
    )
    upload_Date = models.DateField(
        verbose_name=_("Upload Datatime"), default=date.today, blank=True, null=True
    )

    class Meta:
        db_table = "dme_attachments"


class BOK_0_BookingKeys(models.Model):
    pk_auto_id = models.AutoField(primary_key=True)
    client_booking_id = models.CharField(
        verbose_name=_("Client booking id"), max_length=64, blank=True
    )
    filename = models.CharField(
        verbose_name=_("File name"), max_length=128, blank=False
    )
    success = models.CharField(verbose_name=_("Success"), max_length=1)
    timestampCreated = models.DateTimeField(
        verbose_name=_("PickUp Available From"), default=datetime.now, blank=True
    )
    client = models.CharField(
        verbose_name=_("Client"), max_length=64, blank=True, null=True, default=""
    )
    v_client_pk_consigment_num = models.CharField(
        verbose_name=_("Consigment num"), max_length=64, blank=True
    )
    l_000_client_acct_number = models.CharField(
        verbose_name=_("Client account number"), max_length=64, blank=True, null=True
    )
    l_011_client_warehouse_id = models.IntegerField(
        verbose_name=_("Client warehouse Id"), blank=True
    )
    l_012_client_warehouse_name = models.CharField(
        verbose_name=_("Client warehouse Name"), max_length=240, blank=True
    )

    class Meta:
        db_table = "bok_0_bookingkeys"


class BOK_1_headers(models.Model):
    pk_auto_id = models.AutoField(primary_key=True)
    client_booking_id = models.CharField(
        verbose_name=_("Client booking id"), max_length=64, blank=True
    )
    b_021_b_pu_avail_from_date = models.DateField(
        verbose_name=_("Available From"), default=None, blank=True
    )
    b_003_b_service_name = models.CharField(
        verbose_name=_("Service Name"), max_length=31, blank=True, null=True
    )
    b_500_b_client_cust_job_code = models.CharField(
        verbose_name=_("Client Job Code"), max_length=20, blank=True, null=True
    )
    b_054_b_del_company = models.CharField(
        verbose_name=_("Del company"), max_length=100, blank=True, null=True
    )
    b_000_b_total_lines = models.IntegerField(
        verbose_name=_("b_000_b_total_lines"), blank=True, null=True
    )
    b_058_b_del_address_suburb = models.CharField(
        verbose_name=_("Address suburb"), max_length=40, blank=True, null=True
    )
    b_057_b_del_address_state = models.CharField(
        verbose_name=_("Address state"), max_length=20, blank=True, null=True
    )
    b_059_b_del_address_postalcode = models.CharField(
        verbose_name=_("Address Postal Code"),
        max_length=16,
        blank=True,
        null=True,
        default="",
    )
    v_client_pk_consigment_num = models.CharField(
        verbose_name=_("Consigment num"), max_length=64, blank=True, null=True
    )
    total_kg = models.FloatField(verbose_name=_("Total Kg"), blank=True, null=True)
    success = models.CharField(
        verbose_name=_("Success"), max_length=1, default=0, null=True
    )
    fk_client_warehouse = models.ForeignKey(
        Client_warehouses, on_delete=models.CASCADE, default="1"
    )
    b_clientPU_Warehouse = models.CharField(
        verbose_name=_("warehouse"), max_length=32, blank=True, null=True
    )
    fk_client_id = models.CharField(
        verbose_name=_("fk_client_id"), max_length=64, blank=True, null=True
    )
    date_processed = models.DateTimeField(
        verbose_name=_("date_processed"), default=datetime.now, blank=True, null=True
    )
    pk_header_id = models.CharField(
        verbose_name=_("pk_header_id"), max_length=64, blank=True, null=True
    )
    b_000_1_b_clientReference_RA_Numbers = models.CharField(
        verbose_name=_("b_000_1_b_clientReference_RA_Numbers"),
        max_length=500,
        blank=True,
        null=True,
    )
    b_000_2_b_price = models.FloatField(
        verbose_name=_("b_000_2_b_price"),
        max_length=4,
        blank=True,
        default=0,
        null=True,
    )
    b_001_b_freight_provider = models.CharField(
        verbose_name=_("b_001_b_freight_provider"), max_length=36, blank=True, null=True
    )
    b_002_b_vehicle_type = models.CharField(
        verbose_name=_("b_002_b_vehicle_type"), max_length=36, blank=True, null=True
    )
    b_005_b_created_for = models.CharField(
        verbose_name=_("b_005_b_created_for"), max_length=50, blank=True, null=True
    )
    b_006_b_created_for_email = models.CharField(
        verbose_name=_("b_006_b_created_for_email"),
        max_length=64,
        blank=True,
        null=True,
    )
    b_007_b_ready_status = models.CharField(
        verbose_name=_("b_007_b_ready_status"), max_length=24, blank=True, null=True
    )
    b_008_b_category = models.CharField(
        verbose_name=_("b_008_b_category"), max_length=64, blank=True, null=True
    )
    b_009_b_priority = models.CharField(
        verbose_name=_("b_009_b_priority"), max_length=20, blank=True, null=True
    )
    b_010_b_notes = models.CharField(
        verbose_name=_("b_010_b_notes"), max_length=500, blank=True, null=True
    )
    b_012_b_driver_bring_connote = models.BooleanField(
        verbose_name=_("b_012_b_driver_bring_connote"),
        default="False",
        blank=True,
        null=True,
    )
    b_013_b_package_job = models.BooleanField(
        verbose_name=_("b_013_b_package_job"), default=False, blank=True, null=True
    )
    b_014_b_pu_handling_instructions = models.TextField(
        verbose_name=_("b_014_b_pu_handling_instructions"),
        max_length=512,
        blank=True,
        null=True,
    )
    b_015_b_pu_instructions_contact = models.TextField(
        verbose_name=_("b_015_b_pu_instructions_contact"),
        max_length=512,
        blank=True,
        null=True,
    )
    b_016_b_pu_instructions_address = models.TextField(
        verbose_name=_("b_016_b_pu_instructions_address"),
        max_length=512,
        blank=True,
        null=True,
    )
    b_017_b_pu_warehouse_num = models.CharField(
        verbose_name=_("b_017_b_pu_warehouse_num"), max_length=10, blank=True, null=True
    )
    b_018_b_pu_warehouse_bay = models.CharField(
        verbose_name=_("b_018_b_pu_warehouse_bay"), max_length=10, blank=True, null=True
    )
    b_019_b_pu_tail_lift = models.BooleanField(
        verbose_name=_("b_019_b_pu_tail_lift"), default=False, blank=True, null=True
    )
    b_020_b_pu_num_operators = models.BooleanField(
        verbose_name=_("b_020_b_pu_num_operators"), blank=True, default=False, null=True
    )
    b_022_b_pu_avail_from_time_hour = models.IntegerField(
        verbose_name=_("b_022_b_pu_avail_from_time_hour"),
        blank=True,
        default=0,
        null=True,
    )
    b_023_b_pu_avail_from_time_minute = models.IntegerField(
        verbose_name=_("b_023_b_pu_avail_from_time_minute"),
        blank=True,
        default=0,
        null=True,
    )
    b_024_b_pu_by_date = models.DateField(default=None, blank=True, null=True)
    b_025_b_pu_by_time_hour = models.IntegerField(
        verbose_name=_("b_025_b_pu_by_time_hour"), blank=True, default=0, null=True
    )
    b_026_b_pu_by_time_minute = models.IntegerField(
        verbose_name=_("b_026_b_pu_by_time_minute"), blank=True, default=0, null=True
    )
    b_027_b_pu_address_type = models.CharField(
        verbose_name=_("b_027_b_pu_address_type"), max_length=20, blank=True, null=True
    )
    b_028_b_pu_company = models.CharField(
        verbose_name=_("b_028_b_pu_company"), max_length=40, blank=True, null=True
    )
    b_029_b_pu_address_street_1 = models.CharField(
        verbose_name=_("b_029_b_pu_address_street_1"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_030_b_pu_address_street_2 = models.CharField(
        verbose_name=_("b_030_b_pu_address_street_2"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_031_b_pu_address_state = models.CharField(
        verbose_name=_("b_031_b_pu_address_state"), max_length=20, blank=True, null=True
    )
    b_032_b_pu_address_suburb = models.CharField(
        verbose_name=_("b_032_b_pu_address_suburb"),
        max_length=20,
        blank=True,
        null=True,
    )
    b_033_b_pu_address_postalcode = models.CharField(
        verbose_name=_("b_033_b_pu_address_postalcode"),
        max_length=15,
        blank=True,
        null=True,
    )
    b_034_b_pu_address_country = models.CharField(
        verbose_name=_("b_034_b_pu_address_country"),
        max_length=15,
        blank=True,
        null=True,
    )
    b_035_b_pu_contact_full_name = models.CharField(
        verbose_name=_("b_035_b_pu_contact_full_name"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_036_b_pu_email_group = models.TextField(max_length=512, blank=True, null=True)
    b_037_b_pu_email = models.CharField(
        verbose_name=_("b_037_b_pu_email"), max_length=50, blank=True, null=True
    )
    b_038_b_pu_phone_main = models.CharField(
        verbose_name=_("b_038_b_pu_phone_main"), max_length=25, blank=True, null=True
    )
    b_039_b_pu_phone_mobile = models.CharField(
        verbose_name=_("b_039_b_pu_phone_mobile"), max_length=25, blank=True, null=True
    )
    b_040_b_pu_communicate_via = models.CharField(
        verbose_name=_("b_040_b_pu_communicate_via"),
        max_length=30,
        blank=True,
        null=True,
    )
    b_041_b_del_tail_lift = models.BooleanField(
        verbose_name=_("b_041_b_del_tail_lift"), default=False, blank=True, null=True
    )
    b_042_b_del_num_operators = models.BooleanField(
        verbose_name=_("b_042_b_del_num_operators"),
        blank=True,
        default=False,
        null=True,
    )
    b_043_b_del_instructions_contact = models.TextField(
        verbose_name=_("b_043_b_del_instructions_contact"),
        max_length=512,
        blank=True,
        null=True,
    )
    b_044_b_del_instructions_address = models.TextField(
        verbose_name=_("b_044_b_del_instructions_address"),
        max_length=512,
        blank=True,
        null=True,
    )
    b_045_b_del_warehouse_bay = models.CharField(
        verbose_name=_("b_045_b_del_warehouse_bay"),
        max_length=100,
        blank=True,
        null=True,
    )
    b_046_b_del_warehouse_number = models.CharField(
        verbose_name=_("b_046_b_del_warehouse_number"),
        max_length=1,
        blank=True,
        null=True,
    )
    b_047_b_del_avail_from_date = models.DateField(default=None, blank=True, null=True)
    b_048_b_del_avail_from_time_hour = models.IntegerField(
        verbose_name=_("b_048_b_del_avail_from_time_hour"),
        blank=True,
        default=0,
        null=True,
    )
    b_049_b_del_avail_from_time_minute = models.IntegerField(
        verbose_name=_("b_049_b_del_avail_from_time_minute"),
        blank=True,
        default=0,
        null=True,
    )
    b_050_b_del_by_date = models.DateField(default=None, blank=True, null=True)
    b_051_b_del_by_time_hour = models.IntegerField(
        verbose_name=_("b_051_b_del_by_time_hour"), blank=True, default=0, null=True
    )
    b_052_b_del_by_time_minute = models.IntegerField(
        verbose_name=_("b_052_b_del_by_time_minute"), blank=True, default=0, null=True
    )
    b_055_b_del_address_street_1 = models.CharField(
        verbose_name=_("b_055_b_del_address_street_1"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_056_b_del_address_street_2 = models.CharField(
        verbose_name=_("b_056_b_del_address_street_2"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_060_b_del_address_country = models.CharField(
        verbose_name=_("b_060_b_del_address_country"),
        max_length=15,
        blank=True,
        null=True,
    )
    b_061_b_del_contact_full_name = models.CharField(
        verbose_name=_("b_061_b_del_contact_full_name"),
        max_length=50,
        blank=True,
        null=True,
    )
    b_062_b_del_email_group = models.TextField(max_length=512, blank=True, null=True)
    b_063_b_del_email = models.CharField(
        verbose_name=_("b_063_b_del_email"), max_length=50, blank=True, null=True
    )
    b_064_b_del_phone_main = models.CharField(
        verbose_name=_("b_064_b_del_phone_main"), max_length=25, blank=True, null=True
    )
    b_065_b_del_phone_mobile = models.CharField(
        verbose_name=_("b_065_b_del_phone_mobile"), max_length=25, blank=True, null=True
    )
    b_066_b_del_communicate_via = models.CharField(
        verbose_name=_("b_066_b_del_communicate_via"),
        max_length=30,
        blank=True,
        null=True,
    )
    b_500_b_client_UOM = models.CharField(
        verbose_name=_("b_500_b_client_UOM"), max_length=20, blank=True, null=True
    )
    b_501_b_client_code = models.CharField(
        verbose_name=_("b_501_b_client_code"), max_length=50, blank=True, null=True
    )
    pu_addressed_saved = models.CharField(
        verbose_name=_("pu_addressed_saved"), max_length=3, blank=True, null=True
    )
    de_to_addressed_saved = models.CharField(
        verbose_name=_("de_to_addressed_saved"), max_length=3, blank=True, null=True
    )
    b_client_max_book_amount = models.IntegerField(
        verbose_name=_("b_client_max_book_amount"), blank=True, default=0, null=True
    )
    vx_serviceType_XXX = models.CharField(
        verbose_name=_("vx_serviceType_XXX"), max_length=50, blank=True, null=True
    )
    b_053_b_del_address_type = models.CharField(
        verbose_name=_("b_053_b_del_address_type"), max_length=50, blank=True, null=True
    )
    b_client_sales_inv_num = models.CharField(
        verbose_name=_("Sales Inv Num"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    b_client_order_num = models.CharField(
        verbose_name=_("Order Num"), max_length=64, blank=True, null=True, default=""
    )
    b_client_del_note_num = models.CharField(
        verbose_name=_("Del Note Num"), max_length=64, blank=True, null=True, default=""
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )
    b_client_warehouse_code = models.CharField(
        verbose_name=_("Warehouse code"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    fp_pu_id = models.CharField(
        verbose_name=_("Warehouse code"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    b_100_client_price_paid_or_quoted = models.FloatField(
        max_length=64, blank=True, null=True, default=0
    )
    b_000_3_consignment_number = models.CharField(
        max_length=32, blank=True, null=True, default=""
    )
    b_000_0_b_client_agent_code = models.CharField(
        max_length=32, blank=True, null=True, default=None
    )
    x_booking_Created_With = models.CharField(
        verbose_name=_("Booking Created With"), max_length=32, blank=True, null=True,
    )
    z_test = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_101_text_1 = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_102_text_2 = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_103_text_3 = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_104_text_4 = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_105_text_5 = models.CharField(max_length=64, blank=True, null=True, default="")
    zb_121_integer_1 = models.IntegerField(blank=True, default=0, null=True)
    zb_122_integer_2 = models.IntegerField(blank=True, default=0, null=True)
    zb_123_integer_3 = models.IntegerField(blank=True, default=0, null=True)
    zb_124_integer_4 = models.IntegerField(blank=True, default=0, null=True)
    zb_125_integer_5 = models.IntegerField(blank=True, default=0, null=True)
    zb_131_decimal_1 = models.FloatField(blank=True, default=0, null=True)
    zb_132_decimal_2 = models.FloatField(blank=True, default=0, null=True)
    zb_133_decimal_3 = models.FloatField(blank=True, default=0, null=True)
    zb_134_decimal_4 = models.FloatField(blank=True, default=0, null=True)
    zb_135_decimal_5 = models.FloatField(blank=True, default=0, null=True)
    zb_141_date_1 = models.DateField(default=date.today, blank=True, null=True)
    zb_142_date_2 = models.DateField(default=date.today, blank=True, null=True)
    zb_143_date_3 = models.DateField(default=date.today, blank=True, null=True)
    zb_144_date_4 = models.DateField(default=date.today, blank=True, null=True)
    zb_145_date_5 = models.DateField(default=date.today, blank=True, null=True)

    class Meta:
        db_table = "bok_1_headers"


class BOK_2_lines(models.Model):
    pk_lines_id = models.AutoField(primary_key=True)
    success = models.CharField(
        verbose_name=_("Success"), max_length=1, default=0, blank=True, null=True
    )
    fk_header_id = models.CharField(
        verbose_name=_("Header id"), max_length=64, blank=True, null=True
    )
    pk_booking_lines_id = models.CharField(max_length=64, blank=True, null=True)
    client_booking_id = models.CharField(
        verbose_name=_("Client booking id"), max_length=64, blank=True, null=True
    )
    l_501_client_UOM = models.CharField(
        verbose_name=_("Client UOM"), max_length=10, blank=True, null=True
    )
    l_009_weight_per_each = models.FloatField(
        verbose_name=_("Weight per each"), blank=True, null=True
    )
    l_010_totaldim = models.FloatField(
        verbose_name=_("Totaldim"), blank=True, null=True
    )
    l_500_client_run_code = models.CharField(
        verbose_name=_("Client run code"), max_length=7, blank=True, null=True
    )
    l_003_item = models.CharField(
        verbose_name=_("Item"), max_length=128, blank=True, null=True
    )
    l_004_dim_UOM = models.CharField(
        verbose_name=_("DIM UOM"), max_length=10, blank=True, null=True
    )
    v_client_pk_consigment_num = models.CharField(
        verbose_name=_("Consigment num"), max_length=64, blank=True, null=True
    )
    l_cubic_weight = models.FloatField(
        verbose_name=_("Cubic Weight"), blank=True, null=True
    )
    l_002_qty = models.IntegerField(
        verbose_name=_("Address Postal Code"), blank=True, null=True
    )
    e_pallet_type = models.CharField(
        verbose_name=_("Pallet Type"), max_length=24, blank=True, null=True
    )
    e_item_type = models.CharField(
        verbose_name=_("Item Type"), max_length=32, blank=True, null=True
    )
    e_item_type_new = models.CharField(
        verbose_name=_("Item Type New"), max_length=32, blank=True, null=True
    )
    date_processed = models.DateTimeField(
        verbose_name=_("Date Pocessed"), default=datetime.now, blank=True, null=True
    )
    l_001_type_of_packaging = models.CharField(
        verbose_name=_("Type Of Packaging"), max_length=24, blank=True, null=True
    )
    l_005_dim_length = models.FloatField(
        verbose_name=_("DIM Length"), blank=True, null=True
    )
    l_006_dim_width = models.FloatField(
        verbose_name=_("DIM Width"), blank=True, null=True
    )
    l_007_dim_height = models.FloatField(
        verbose_name=_("DIM Height"), blank=True, null=True
    )
    l_008_weight_UOM = models.CharField(
        verbose_name=_("DIM Weight"), max_length=10, default="", blank=True, null=True
    )
    l_009_weight_per_each_original = models.IntegerField(
        verbose_name=_("Weight Per Each Original"), blank=True, null=True
    )
    l_500_b_client_cust_job_code = models.CharField(
        verbose_name=_("Client Cust Job Code"), max_length=32, blank=True, null=True
    )
    client_item_number = models.CharField(
        max_length=64, blank=True, null=True, default=""
    )
    client_item_reference = models.CharField(
        max_length=64, blank=True, null=True, default=""
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )
    zbl_101_text_1 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbl_102_text_2 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbl_103_text_3 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbl_104_text_4 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbl_105_text_5 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbl_121_integer_1 = models.IntegerField(blank=True, default=0, null=True)
    zbl_122_integer_2 = models.IntegerField(blank=True, default=0, null=True)
    zbl_123_integer_3 = models.IntegerField(blank=True, default=0, null=True)
    zbl_124_integer_4 = models.IntegerField(blank=True, default=0, null=True)
    zbl_125_integer_5 = models.IntegerField(blank=True, default=0, null=True)
    zbl_131_decimal_1 = models.FloatField(blank=True, default=0, null=True)
    zbl_132_decimal_2 = models.FloatField(blank=True, default=0, null=True)
    zbl_133_decimal_3 = models.FloatField(blank=True, default=0, null=True)
    zbl_134_decimal_4 = models.FloatField(blank=True, default=0, null=True)
    zbl_135_decimal_5 = models.FloatField(blank=True, default=0, null=True)
    zbl_141_date_1 = models.DateField(default=date.today, blank=True, null=True)
    zbl_142_date_2 = models.DateField(default=date.today, blank=True, null=True)
    zbl_143_date_3 = models.DateField(default=date.today, blank=True, null=True)
    zbl_144_date_4 = models.DateField(default=date.today, blank=True, null=True)
    zbl_145_date_5 = models.DateField(default=date.today, blank=True, null=True)

    class Meta:
        db_table = "bok_2_lines"


class BOK_3_lines_data(models.Model):
    pk_auto_id = models.AutoField(primary_key=True)
    client_booking_id = models.CharField(
        verbose_name=_("Client booking id"), max_length=64, blank=True, null=True
    )
    fk_header_id = models.CharField(max_length=64, blank=True)
    fk_booking_lines_id = models.CharField(max_length=64, blank=True, default=None)
    v_client_pk_consigment_num = models.CharField(
        verbose_name=_("Consigment num"), max_length=64, blank=True, null=True
    )
    ld_001_qty = models.IntegerField(verbose_name=_("Quantity"), blank=True, null=True)
    ld_002_model_number = models.CharField(
        verbose_name=_("Consigment num"), max_length=40, blank=True, null=True
    )
    ld_003_item_description = models.TextField(
        verbose_name=_("Item Description"), max_length=500, blank=True, null=True
    )
    ld_004_fault_description = models.CharField(
        verbose_name=_("fault Description"), max_length=500, blank=True, null=True
    )
    ld_005_item_serial_number = models.CharField(
        verbose_name=_("Item Serial Number"), max_length=40, blank=True, null=True
    )
    ld_006_insurance_value = models.IntegerField(
        verbose_name=_("Insurance Value"), blank=True, null=True
    )
    ld_007_gap_ra = models.TextField(
        verbose_name=_("Gap Ra"), max_length=300, blank=True, null=True
    )
    ld_008_client_ref_number = models.CharField(
        verbose_name=_("Client Ref Number"), max_length=40, blank=True, null=True
    )
    success = models.CharField(
        verbose_name=_("Success"), max_length=1, default=2, blank=True, null=True
    )
    zbld_101_text_1 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbld_102_text_2 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbld_103_text_3 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbld_104_text_4 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbld_105_text_5 = models.CharField(max_length=64, blank=True, null=True, default="")
    zbld_121_integer_1 = models.IntegerField(blank=True, default=0, null=True)
    zbld_122_integer_2 = models.IntegerField(blank=True, default=0, null=True)
    zbld_123_integer_3 = models.IntegerField(blank=True, default=0, null=True)
    zbld_124_integer_4 = models.IntegerField(blank=True, default=0, null=True)
    zbld_125_integer_5 = models.IntegerField(blank=True, default=0, null=True)
    zbld_131_decimal_1 = models.FloatField(blank=True, default=0, null=True)
    zbld_132_decimal_2 = models.FloatField(blank=True, default=0, null=True)
    zbld_133_decimal_3 = models.FloatField(blank=True, default=0, null=True)
    zbld_134_decimal_4 = models.FloatField(blank=True, default=0, null=True)
    zbld_135_decimal_5 = models.FloatField(blank=True, default=0, null=True)
    zbld_141_date_1 = models.DateField(default=date.today, blank=True, null=True)
    zbld_142_date_2 = models.DateField(default=date.today, blank=True, null=True)
    zbld_143_date_3 = models.DateField(default=date.today, blank=True, null=True)
    zbld_144_date_4 = models.DateField(default=date.today, blank=True, null=True)
    zbld_145_date_5 = models.DateField(default=date.today, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created By Account"), max_length=25, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), default=datetime.now, blank=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified By Account"), max_length=25, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), default=datetime.now, blank=True
    )

    class Meta:
        db_table = "bok_3_lines_data"


class Log(models.Model):
    id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("FK Booking Id"), max_length=64, blank=True, null=True
    )
    request_payload = models.TextField(
        verbose_name=_("Request Payload"), max_length=2000, blank=True, default=""
    )
    response = models.TextField(
        verbose_name=_("Response"), max_length=10000, blank=True, default=""
    )
    request_timestamp = models.DateTimeField(
        verbose_name=_("Request Timestamp"), default=datetime.now, blank=True
    )
    request_status = models.CharField(
        verbose_name=_("Request Status"), max_length=20, blank=True, default=""
    )
    request_type = models.CharField(
        verbose_name=_("Request Type"), max_length=30, blank=True, default=""
    )
    fk_service_provider_id = models.CharField(
        verbose_name=_("Service Provider ID"), max_length=36, blank=True, default=""
    )
    z_temp_success_seaway_history = models.BooleanField(
        verbose_name=_("Passed by log script"), default=False, blank=True, null=True
    )
    z_createdBy = models.CharField(
        verbose_name=_("Created By"), max_length=40, blank=True, default=""
    )
    z_modifiedBy = models.CharField(
        verbose_name=_("Modified By"), max_length=40, blank=True, default=""
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_log"


class Api_booking_confirmation_lines(models.Model):
    id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    fk_booking_line_id = models.CharField(
        verbose_name=_("Booking Line ID"), max_length=64, blank=True, null=True
    )
    kf_booking_confirmation_id = models.CharField(
        verbose_name=_("Booking Confimration ID"), max_length=64, blank=True, null=True
    )
    pk_booking_confirmation_lines = models.IntegerField(
        verbose_name=_("Booking confirmation lines"), blank=True, null=True
    )
    fk_api_results_id = models.IntegerField(
        verbose_name=_("Result ID"), blank=True, null=True
    )
    service_provider = models.CharField(
        verbose_name=_("Service Provider"), max_length=64, blank=True, null=True
    )
    api_artical_id = models.CharField(
        verbose_name=_("Artical ID"), max_length=64, blank=True, null=True
    )
    api_consignment_id = models.CharField(
        verbose_name=_("Consignment ID"), max_length=64, blank=True, null=True
    )
    api_cost = models.CharField(
        verbose_name=_("Cost"), max_length=64, blank=True, null=True
    )
    api_gst = models.CharField(
        verbose_name=_("GST"), max_length=64, blank=True, null=True
    )
    api_item_id = models.CharField(
        verbose_name=_("Item ID"), max_length=64, blank=True, null=True
    )
    api_item_reference = models.CharField(
        verbose_name=_("Item Reference"), max_length=64, blank=True, null=True
    )
    api_product_id = models.CharField(
        verbose_name=_("Product ID"), max_length=64, blank=True, null=True
    )
    api_status = models.CharField(
        verbose_name=_("Status"), max_length=64, blank=True, null=True
    )
    label_code = models.CharField(max_length=64, blank=True, null=True)
    client_item_reference = models.CharField(
        max_length=64, blank=True, null=True, default=""
    )
    fp_event_date = models.DateField(blank=True, null=True)
    fp_event_time = models.TimeField(blank=True, null=True)
    fp_scan_data = models.CharField(max_length=64, blank=True, null=True, default="")
    tally = models.IntegerField(blank=True, null=True, default=0)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "api_booking_confirmation_lines"


class Api_booking_quotes_confirmation(models.Model):
    id = models.AutoField(primary_key=True)
    api_shipment_id = models.CharField(
        verbose_name=_("API shipment ID"), max_length=64, blank=True, null=True
    )
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    kf_order_id = models.CharField(
        verbose_name=_("Order ID"), max_length=64, blank=True, null=True
    )
    fk_freight_provider_id = models.CharField(
        verbose_name=_("Freight Provider ID"), max_length=64, blank=True, null=True
    )
    fk_booking_quote_confirmation = models.CharField(
        verbose_name=_("Freight Provider ID"), max_length=64, blank=True, null=True
    )
    job_date = models.DateTimeField(
        verbose_name=_("Job Date"), default=datetime.now, blank=True, null=True
    )
    provider = models.CharField(
        verbose_name=_("Provider"), max_length=64, blank=True, null=True
    )
    tracking_number = models.CharField(
        verbose_name=_("Tracking Number"), max_length=64, blank=True, null=True
    )
    job_number = models.CharField(
        verbose_name=_("Job Number"), max_length=64, blank=True, null=True
    )
    api_number_of_shipment_items = models.CharField(
        verbose_name=_("API Number Of Shipment Items"),
        max_length=64,
        blank=True,
        null=True,
    )
    etd = models.CharField(verbose_name=_("ETD"), max_length=64, blank=True, null=True)
    fee = models.FloatField(verbose_name=_("Fee"), blank=True, null=True)
    tax_id_1 = models.CharField(
        verbose_name=_("Tax ID 1"), max_length=10, blank=True, null=True
    )
    tax_value_1 = models.IntegerField(
        verbose_name=_("Tax Value 1"), blank=True, null=True
    )
    tax_id_2 = models.CharField(
        verbose_name=_("Tax ID 2"), max_length=10, blank=True, null=True
    )
    tax_value_2 = models.IntegerField(
        verbose_name=_("Tax Value 2"), blank=True, null=True
    )
    tax_id_3 = models.CharField(
        verbose_name=_("Tax ID 3"), max_length=10, blank=True, null=True
    )
    tax_value_3 = models.IntegerField(
        verbose_name=_("Tax Value 3"), blank=True, null=True
    )
    tax_id_4 = models.CharField(
        verbose_name=_("Tax ID 4"), max_length=10, blank=True, null=True
    )
    tax_value_4 = models.IntegerField(
        verbose_name=_("Tax Value 4"), blank=True, null=True
    )
    tax_id_5 = models.CharField(
        verbose_name=_("Tax ID 5"), max_length=10, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "api_booking_quotes_confirmation"


class Utl_suburbs(models.Model):
    id = models.AutoField(primary_key=True)
    postal_code = models.CharField(
        verbose_name=_("Postal Code"), max_length=64, blank=True, null=True
    )
    fk_state_id = models.IntegerField(
        verbose_name=_("FK State ID"), blank=True, null=False, default=0
    )
    state = models.CharField(
        verbose_name=_("State"), max_length=64, blank=True, null=True
    )
    suburb = models.CharField(
        verbose_name=_("Suburb"), max_length=64, blank=True, null=True
    )
    ROUTING_ZONE = models.CharField(
        verbose_name=_("Routing Zone"), max_length=64, blank=True, null=True
    )
    ROUTING_CODE = models.CharField(
        verbose_name=_("Routing Code"), max_length=64, blank=True, null=True
    )
    RATING_ZONE_DIRECT = models.CharField(
        verbose_name=_("Rating Zone Direct"), max_length=64, blank=True, null=True
    )
    RATING_ZONE_MEGA = models.CharField(
        verbose_name=_("Rating Zone Mega"), max_length=64, blank=True, null=True
    )
    category = models.CharField(
        verbose_name=_("Category"), max_length=64, blank=True, null=True
    )
    z_BorderExpressEmailForState = models.CharField(
        verbose_name=_("Border Express Email For State"),
        max_length=64,
        blank=True,
        null=True,
    )
    comment = models.CharField(
        verbose_name=_("Comment"), max_length=64, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_suburbs"


class Utl_states(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(
        verbose_name=_("Type"), max_length=64, blank=True, null=True
    )
    fk_country_id = models.CharField(max_length=32, blank=True, null=True, default="")
    pk_state_id = models.IntegerField(
        verbose_name=_("PK State ID"), blank=True, null=False, default=0
    )
    state_code = models.CharField(
        verbose_name=_("State Code"), max_length=10, blank=True, null=True
    )
    state_name = models.CharField(
        verbose_name=_("State Name"), max_length=64, blank=True, null=True
    )
    sender_code = models.CharField(
        verbose_name=_("Sender Code"), max_length=64, blank=True, null=True
    )
    borderExpress_pu_emails = models.CharField(
        verbose_name=_("Border Express PU Emails"), max_length=64, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_states"


class Utl_country_codes(models.Model):
    id = models.AutoField(primary_key=True)
    pk_country_id = models.IntegerField(
        verbose_name=_("PK Country Id"), blank=True, null=False, default=0
    )
    country_code_abbr = models.CharField(
        verbose_name=_("Country Code Abbr"), max_length=16, blank=True, null=True
    )
    country_name = models.CharField(
        verbose_name=_("Country Name"), max_length=36, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_country_codes"


class Utl_sql_queries(models.Model):
    id = models.AutoField(primary_key=True)
    sql_title = models.CharField(
        verbose_name=_("SQL Title"), max_length=36, blank=True, null=True
    )
    sql_query = models.TextField(verbose_name=_("SQL Query"), blank=True, null=True)
    sql_description = models.TextField(
        verbose_name=_("SQL Description"), blank=True, null=True
    )
    sql_notes = models.TextField(verbose_name=_("SQL Notes"), blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_sql_queries"


class Dme_status_history(models.Model):
    id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    status_from_api = models.CharField(
        verbose_name=_("Status From API"),
        max_length=50,
        blank=True,
        default="",
        null=True,
    )
    status_code_api = models.CharField(
        verbose_name=_("Status Code API"),
        max_length=50,
        blank=True,
        default="",
        null=True,
    )
    status_last = models.CharField(
        verbose_name=_("Status Last"), max_length=64, blank=True, null=True
    )
    notes = models.CharField(
        verbose_name=_("Notes"), max_length=200, blank=True, null=True
    )
    communicate_tick = models.BooleanField(
        verbose_name=_("Communicate Tick"), default=False, blank=True, null=True
    )
    notes_type = models.CharField(
        verbose_name=_("Notes Type"), max_length=24, blank=True, null=True
    )
    status_old = models.CharField(
        verbose_name=_("Status Old"), max_length=64, blank=True, null=True
    )
    api_status_pretranslation = models.CharField(
        verbose_name=_("Api Status Pretranslation"),
        max_length=64,
        blank=True,
        null=True,
    )
    booking_request_data = models.CharField(
        verbose_name=_("Booking Request Data"), max_length=64, blank=True, null=True
    )
    request_dates = models.CharField(
        verbose_name=_("Request Dates"), max_length=64, blank=True, null=True
    )
    recipient_name = models.CharField(
        verbose_name=_("Recipient Name"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )
    fk_fp_id = models.CharField(
        verbose_name=_("FP ID"), max_length=64, blank=True, default="", null=True
    )
    depot_name = models.CharField(
        verbose_name=_("Depot Name"), max_length=64, blank=True, default="", null=True
    )
    dme_notes = models.TextField(
        verbose_name=_("DME notes"), max_length=500, blank=True, default="", null=True
    )
    event_time_stamp = models.DateTimeField(
        verbose_name=_("Event Timestamp"), default=datetime.now, blank=True, null=True
    )
    status_update_via = models.CharField(
        verbose_name=_("Status Updated Via"), max_length=64, blank=True, null=True
    )  # one of 3 - fp api, manual, excel
    dme_status_detail = models.TextField(
        max_length=500, blank=True, null=True, default=""
    )
    dme_status_action = models.TextField(
        max_length=500, blank=True, null=True, default=""
    )
    dme_status_linked_reference_from_fp = models.TextField(
        max_length=150, blank=True, null=True, default=""
    )
    b_booking_visualID = models.CharField(max_length=64, blank=True, null=True)
    b_status_api = models.CharField(max_length=64, blank=True, null=True)
    total_scanned = models.IntegerField(blank=True, null=False, default=0)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_status_history"

    def is_last_status_of_booking(self, booking):
        status_histories = Dme_status_history.objects.filter(
            fk_booking_id=booking.pk_booking_id
        ).order_by("id")

        if status_histories.exists():
            if self.pk == status_histories.last().pk:
                return True

        return False


class Dme_urls(models.Model):
    id = models.AutoField(primary_key=True)
    url = models.CharField(verbose_name=_("URL"), max_length=255, blank=True, null=True)
    description = models.CharField(
        verbose_name=_("Description"), max_length=255, blank=True, null=True
    )

    class Meta:
        db_table = "dme_urls"


class Dme_log_addr(models.Model):
    id = models.AutoField(primary_key=True)
    addresses = models.TextField(
        verbose_name=_("Address Info"), blank=True, null=True, default=""
    )
    fk_booking_id = models.CharField(
        verbose_name=_("Description"), max_length=255, blank=True, null=True, default=""
    )
    consignmentNumber = models.CharField(
        verbose_name=_("Consignment Number"),
        max_length=255,
        blank=True,
        null=True,
        default="",
    )
    length = models.FloatField(
        verbose_name=_("Length"), blank=True, null=True, default=0
    )
    width = models.FloatField(verbose_name=_("Width"), blank=True, null=True, default=0)
    height = models.FloatField(
        verbose_name=_("Height"), blank=True, null=True, default=0
    )
    weight = models.FloatField(
        verbose_name=_("Height"), blank=True, null=True, default=0
    )

    class Meta:
        db_table = "dme_log_addr"


class Dme_comm_and_task(models.Model):
    id = models.AutoField(primary_key=True)
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    assigned_to = models.CharField(
        verbose_name=_("Assigned To"), max_length=64, blank=True, null=True
    )
    priority_of_log = models.CharField(
        verbose_name=_("Priority Of Log"), max_length=64, blank=True, null=True
    )
    dme_action = models.TextField(
        verbose_name=_("DME Action"), max_length=4000, blank=True, null=True
    )
    dme_com_title = models.TextField(
        verbose_name=_("DME Comm Title"), max_length=4000, blank=True, null=True
    )
    dme_detail = models.CharField(
        verbose_name=_("DME Detail"), max_length=255, blank=True, null=True
    )
    dme_notes_type = models.CharField(
        verbose_name=_("DME Notes Type"), max_length=64, blank=True, null=True
    )
    dme_notes_external = models.TextField(
        verbose_name=_("DME Notes External"), max_length=4096, blank=True, null=True
    )
    status = models.CharField(
        verbose_name=_("Status"), max_length=32, blank=True, null=True
    )
    query = models.CharField(
        verbose_name=_("Query"), max_length=254, blank=True, null=True
    )
    closed = models.BooleanField(
        verbose_name=_("Closed"), blank=True, null=True, default=False
    )
    due_by_date = models.DateField(verbose_name=_("Due By Date"), blank=True, null=True)
    due_by_time = models.TimeField(verbose_name=_("Due By Time"), blank=True, null=True)
    due_by_new_date = models.DateField(
        verbose_name=_("Due By New Date"), blank=True, null=True
    )
    due_by_new_time = models.TimeField(
        verbose_name=_("Due By New Time"), blank=True, null=True
    )
    final_due_date_time = models.DateTimeField(
        verbose_name=_("Final Due Date Time"), blank=True, null=True
    )
    status_log_closed_time = models.DateTimeField(
        verbose_name=_("Status Log Closed Time"), blank=True, null=True
    )
    z_snooze_option = models.FloatField(
        verbose_name=_("Snooze Option"), blank=True, null=True
    )
    z_time_till_due_sec = models.FloatField(
        verbose_name=_("Time Till Due Second"), blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_comm_and_task"


class Dme_comm_notes(models.Model):
    id = models.AutoField(primary_key=True)
    comm = models.ForeignKey(Dme_comm_and_task, on_delete=models.CASCADE)
    username = models.CharField(
        verbose_name=_("User"), max_length=64, blank=True, null=True
    )
    dme_notes = models.TextField(verbose_name=_("DME Notes"), blank=True, null=True)
    dme_notes_type = models.CharField(
        verbose_name=_("DME Notes Type"), max_length=64, blank=True, null=True
    )
    dme_notes_no = models.IntegerField(
        verbose_name=_("DME Notes No"), blank=False, null=False, default=1
    )
    note_date_created = models.DateField(
        verbose_name=_("Date First"), blank=True, null=True
    )
    note_date_updated = models.DateField(
        verbose_name=_("Date Modified"), blank=True, null=True
    )
    note_time_created = models.TimeField(
        verbose_name=_("Time First"), blank=True, null=True
    )
    note_time_updated = models.TimeField(
        verbose_name=_("Time Modified"), blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_comm_notes"


class Dme_status_notes(models.Model):
    id = models.AutoField(primary_key=True)
    status = models.CharField(
        verbose_name=_("status"), max_length=64, blank=True, null=True
    )

    class Meta:
        db_table = "dme_status_notes"


class Dme_package_types(models.Model):
    id = models.AutoField(primary_key=True)
    dmePackageTypeCode = models.CharField(
        verbose_name=_("DME Package Type Code"), max_length=25, blank=True, null=True
    )
    dmePackageCategory = models.CharField(
        verbose_name=_("DME Package Category"), max_length=25, blank=True, null=True
    )
    dmePackageTypeDesc = models.CharField(
        verbose_name=_("DME Package Type Desc"), max_length=50, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_package_types"


class Utl_dme_status(models.Model):
    id = models.AutoField(primary_key=True)
    phone = models.IntegerField(verbose_name=_("phone number"), null=True, blank=True)
    dme_delivery_status_category = models.CharField(
        max_length=64, blank=True, null=True
    )
    dme_delivery_status = models.CharField(max_length=64, blank=True, null=True)
    dev_notes = models.TextField(max_length=400, blank=True, null=True)
    sort_order = models.FloatField(verbose_name=_("sort order"), default=1)
    z_show_client_option = models.BooleanField(null=True, blank=True, default=False)
    dme_status_label = models.CharField(max_length=128, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_dme_status"


class Dme_utl_fp_statuses(models.Model):
    id = models.AutoField(primary_key=True)
    fk_fp_id = models.IntegerField(default=1, blank=True, null=True)
    fp_name = models.CharField(max_length=50, blank=True, null=True)
    fp_original_status = models.TextField(max_length=400, blank=True, null=True)
    fp_lookup_status = models.TextField(max_length=400, blank=True, null=True)
    fp_status_description = models.TextField(
        max_length=1024, blank=True, null=True, default=""
    )
    dme_status = models.CharField(max_length=150, blank=True, null=True)
    if_scan_total_in_booking_greaterthanzero = models.CharField(
        max_length=32, blank=True, null=True
    )
    pod_delivery_override = models.BooleanField(blank=True, null=True, default=False)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_utl_fp_statuses"


class Dme_utl_client_customer_group(models.Model):
    id = models.AutoField(primary_key=True)
    fk_client_id = models.CharField(max_length=11, blank=True, null=True)
    name_lookup = models.CharField(max_length=50, blank=True, null=True)
    group_name = models.CharField(max_length=64, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_utl_client_customer_group"


class Utl_fp_delivery_times(models.Model):
    id = models.AutoField(primary_key=True)
    fk_fp_id = models.IntegerField(default=1, blank=True, null=True)
    fp_name = models.CharField(max_length=50, blank=True, null=True)
    postal_code_from = models.IntegerField(default=1, blank=True, null=True)
    postal_code_to = models.IntegerField(default=1, blank=True, null=True)
    delivery_days = models.FloatField(default=7, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_fp_delivery_times"


class Utl_dme_status_details(models.Model):
    id = models.AutoField(primary_key=True)
    dme_status_detail = models.TextField(max_length=500, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_dme_status_details"


class Utl_dme_status_actions(models.Model):
    id = models.AutoField(primary_key=True)
    dme_status_action = models.TextField(max_length=500, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "utl_dme_status_actions"


class FP_zones(models.Model):
    id = models.AutoField(primary_key=True)
    suburb = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=16, blank=True, null=True)
    zone = models.CharField(max_length=50, blank=True, null=True)
    carrier = models.CharField(max_length=50, blank=True, null=True)
    service = models.CharField(max_length=50, blank=True, null=True)
    sender_code = models.CharField(max_length=50, blank=True, null=True)
    fk_fp = models.CharField(max_length=32, blank=True, null=True, default=None)
    start_postal_code = models.CharField(
        max_length=16, blank=True, null=True, default=None
    )
    end_postal_code = models.CharField(
        max_length=16, blank=True, null=True, default=None
    )

    class Meta:
        db_table = "fp_zones"


class FP_carriers(models.Model):
    id = models.AutoField(primary_key=True)
    fk_fp = models.CharField(max_length=32, blank=True, null=True, default=None)
    carrier = models.CharField(max_length=50, blank=True, null=True)
    connote_start_value = models.IntegerField(default=None, blank=True, null=True)
    connote_end_value = models.IntegerField(default=None, blank=True, null=True)
    label_start_value = models.IntegerField(default=None, blank=True, null=True)
    label_end_value = models.IntegerField(default=None, blank=True, null=True)
    current_value = models.IntegerField(default=None, blank=True, null=True)

    class Meta:
        db_table = "fp_carriers"


class FP_label_scans(models.Model):
    id = models.AutoField(primary_key=True)
    fk_fp = models.CharField(max_length=32, blank=True, null=True, default=None)
    label_code = models.CharField(max_length=32, blank=True, null=True, default=None)
    client_item_reference = models.CharField(
        max_length=32, blank=True, null=True, default=None
    )
    scanned_date = models.DateField(blank=True, null=True, default=None)
    scanned_time = models.TimeField(blank=True, null=True, default=None)
    scanned_by = models.CharField(max_length=32, blank=True, null=True, default=None)
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "fp_label_scans"


class DME_reports(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, blank=True, null=True)
    type = models.CharField(max_length=32, blank=True, null=True)
    url = models.TextField(max_length=512, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_reports"


class DME_Label_Settings(models.Model):
    id = models.AutoField(primary_key=True)
    uom = models.CharField(max_length=24, blank=True, null=True, default="")
    font_family = models.CharField(max_length=128, blank=True, null=True)
    font_size_small = models.FloatField(blank=True, null=True, default=0)
    font_size_medium = models.FloatField(blank=True, null=True, default=0)
    font_size_large = models.FloatField(blank=True, null=True, default=0)
    label_dimension_length = models.FloatField(blank=True, null=True, default=0)
    label_dimension_width = models.FloatField(blank=True, null=True, default=0)
    label_image_size_length = models.FloatField(blank=True, null=True, default=0)
    label_image_size_width = models.FloatField(blank=True, null=True, default=0)
    barcode_dimension_length = models.FloatField(blank=True, null=True, default=0)
    barcode_dimension_width = models.FloatField(blank=True, null=True, default=0)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "label_settings"


class DME_Email_Templates(models.Model):
    id = models.AutoField(primary_key=True)
    fk_idEmailParent = models.IntegerField(blank=True, null=True, default=0)
    emailName = models.CharField(max_length=255, blank=True, null=True)
    emailBody = models.TextField(blank=True, null=True)
    sectionName = models.TextField(max_length=255, blank=True, null=True)
    emailBodyRepeatEven = models.TextField(max_length=2048, blank=True, null=True)
    emailBodyRepeatOdd = models.TextField(max_length=2048, blank=True, null=True)
    whenAttachmentUnavailable = models.TextField(blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_email_templates"


class DME_Options(models.Model):
    id = models.AutoField(primary_key=True)
    option_name = models.CharField(max_length=255, blank=True, null=False)
    option_value = models.CharField(max_length=8, blank=True, null=False)
    option_description = models.TextField(max_length=1024, blank=True, null=False)
    option_schedule = models.IntegerField(blank=True, null=True, default=0)
    start_time = models.DateTimeField(default=None, blank=True, null=True)
    end_time = models.DateTimeField(default=None, blank=True, null=True)
    start_count = models.IntegerField(blank=True, null=True, default=0)
    end_count = models.IntegerField(blank=True, null=True, default=0)
    elapsed_seconds = models.IntegerField(blank=True, null=True, default=0)
    is_running = models.BooleanField(blank=True, null=True, default=False)
    show_in_admin = models.BooleanField(blank=True, null=True, default=False)
    arg1 = models.IntegerField(blank=True, null=True, default=0)
    arg2 = models.DateTimeField(blank=True, null=True, default=None)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_options"


class FP_Store_Booking_Log(models.Model):
    id = models.AutoField(primary_key=True)
    v_FPBookingNumber = models.CharField(
        max_length=40, blank=True, null=True, default=None,
    )
    delivery_booking = models.DateField(default=None, blank=True, null=True)
    fp_store_event_date = models.DateField(default=None, blank=True, null=True)
    fp_store_event_time = models.TimeField(default=None, blank=True, null=True)
    fp_store_event_desc = models.CharField(
        max_length=255, blank=True, null=True, default=None,
    )
    csv_file_name = models.CharField(
        max_length=255, blank=True, null=True, default=None,
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), default=datetime.now
    )

    class Meta:
        db_table = "fp_store_booking_log"


class FP_vehicles(models.Model):
    id = models.AutoField(primary_key=True)
    freight_provider = models.ForeignKey(Fp_freight_providers, on_delete=models.CASCADE)
    description = models.CharField(max_length=64, blank=True, null=True, default=None,)
    dim_UOM = models.CharField(max_length=16, blank=True, null=True, default=None,)
    max_length = models.FloatField(default=0, null=True, blank=True)
    max_width = models.FloatField(default=0, null=True, blank=True)
    max_height = models.FloatField(default=0, null=True, blank=True)
    mass_UOM = models.CharField(max_length=16, blank=True, null=True, default=None,)
    max_mass = models.IntegerField(default=0, null=True, blank=True)
    pallets = models.IntegerField(default=0, null=True, blank=True)
    pallet_UOM = models.CharField(max_length=16, blank=True, null=True, default=None,)
    max_pallet_length = models.FloatField(default=0, null=True, blank=True)
    max_pallet_width = models.FloatField(default=0, null=True, blank=True)
    max_pallet_height = models.FloatField(default=0, null=True, blank=True)
    base_charge = models.IntegerField(default=0, null=True, blank=True)
    min_charge = models.IntegerField(default=0, null=True, blank=True)
    limited_state = models.CharField(
        max_length=16, blank=True, null=True, default=None,
    )

    class Meta:
        db_table = "fp_vehicles"


class FP_availabilities(models.Model):
    id = models.AutoField(primary_key=True)
    freight_provider = models.ForeignKey(Fp_freight_providers, on_delete=models.CASCADE)
    code = models.CharField(max_length=64, blank=True, null=True, default=None,)
    mon_start = models.TimeField(default=None, blank=True, null=True)
    mon_end = models.TimeField(default=None, blank=True, null=True)
    tue_start = models.TimeField(default=None, blank=True, null=True)
    tue_end = models.TimeField(default=None, blank=True, null=True)
    wed_start = models.TimeField(default=None, blank=True, null=True)
    wed_end = models.TimeField(default=None, blank=True, null=True)
    thu_start = models.TimeField(default=None, blank=True, null=True)
    thu_end = models.TimeField(default=None, blank=True, null=True)
    fri_start = models.TimeField(default=None, blank=True, null=True)
    fri_end = models.TimeField(default=None, blank=True, null=True)
    sat_start = models.TimeField(default=None, blank=True, null=True)
    sat_end = models.TimeField(default=None, blank=True, null=True)
    sun_start = models.TimeField(default=None, blank=True, null=True)
    sun_end = models.TimeField(default=None, blank=True, null=True)

    class Meta:
        db_table = "fp_availabilities"


class FP_costs(models.Model):
    id = models.AutoField(primary_key=True)
    UOM_charge = models.CharField(max_length=16, blank=True, null=True, default=None,)
    start_qty = models.IntegerField(default=0, null=True, blank=True)
    end_qty = models.IntegerField(default=0, null=True, blank=True)
    basic_charge = models.FloatField(default=0, null=True, blank=True)
    min_charge = models.FloatField(default=0, null=True, blank=True)
    per_UOM_charge = models.FloatField(default=0, null=True, blank=True)
    oversize_premium = models.FloatField(default=0, null=True, blank=True)
    oversize_price = models.FloatField(default=0, null=True, blank=True)
    m3_to_kg_factor = models.IntegerField(default=0, null=True, blank=True)
    dim_UOM = models.CharField(max_length=16, blank=True, null=True, default=None,)
    price_up_to_length = models.FloatField(default=0, null=True, blank=True)
    price_up_to_width = models.FloatField(default=0, null=True, blank=True)
    price_up_to_height = models.FloatField(default=0, null=True, blank=True)
    weight_UOM = models.CharField(max_length=16, blank=True, null=True, default=None,)
    price_up_to_weight = models.FloatField(default=0, null=True, blank=True)
    max_length = models.FloatField(default=0, null=True, blank=True)
    max_width = models.FloatField(default=0, null=True, blank=True)
    max_height = models.FloatField(default=0, null=True, blank=True)
    max_weight = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        db_table = "fp_costs"


class FP_pricing_rules(models.Model):
    id = models.AutoField(primary_key=True)
    freight_provider = models.ForeignKey(Fp_freight_providers, on_delete=models.CASCADE)
    cost = models.ForeignKey(FP_costs, on_delete=models.CASCADE, null=True)
    etd = models.ForeignKey(FP_Service_ETDs, on_delete=models.CASCADE, null=True)
    vehicle = models.ForeignKey(
        FP_vehicles, on_delete=models.CASCADE, null=True, default=None
    )
    service_type = models.CharField(max_length=64, blank=True, null=True, default=None,)
    service_timing_code = models.CharField(
        max_length=32, blank=True, null=True, default=None,
    )
    both_way = models.BooleanField(blank=True, null=True, default=False)
    pu_zone = models.CharField(max_length=16, blank=True, null=True, default=None)
    pu_state = models.CharField(max_length=32, blank=True, null=True, default=None)
    pu_postal_code = models.CharField(max_length=8, blank=True, null=True, default=None)
    pu_suburb = models.CharField(max_length=32, blank=True, null=True, default=None)
    de_zone = models.CharField(max_length=16, blank=True, null=True, default=None)
    de_state = models.CharField(max_length=32, blank=True, null=True, default=None)
    de_postal_code = models.CharField(max_length=8, blank=True, null=True, default=None)
    de_suburb = models.CharField(max_length=32, blank=True, null=True, default=None)

    class Meta:
        db_table = "fp_pricing_rules"


@receiver(pre_save, sender=Bookings)
def pre_save_booking(sender, instance: Bookings, **kwargs):
    if instance.id is None:  # new object will be created
        pass
    else:
        previous = Bookings.objects.get(id=instance.id)

        if (
            previous.dme_status_detail != instance.dme_status_detail
        ):  # field will be updated
            instance.dme_status_detail_updated_by = "user"
            instance.prev_dme_status_detail = previous.dme_status_detail
            instance.dme_status_detail_updated_at = datetime.now()

        if previous.b_status != instance.b_status:
            try:
                if instance.b_status == "In Transit":
                    booking_Lines_cnt = Booking_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id
                    ).count()
                    fp_scanned_cnt = Api_booking_confirmation_lines.objects.filter(
                        fk_booking_id=instance.pk_booking_id, tally__gt=0
                    ).count()

                    dme_status_detail = ""
                    if (
                        instance.b_given_to_transport_date_time
                        and not instance.fp_received_date_time
                    ):
                        dme_status_detail = "In transporter's depot"
                    if instance.fp_received_date_time:
                        dme_status_detail = "Good Received by Transport"

                    if fp_scanned_cnt > 0 and fp_scanned_cnt < booking_Lines_cnt:
                        dme_status_detail = dme_status_detail + " (Partial)"

                    instance.dme_status_detail = dme_status_detail
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = previous.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
                elif instance.b_status == "Delivered":
                    instance.dme_status_detail = ""
                    instance.dme_status_detail_updated_by = "user"
                    instance.prev_dme_status_detail = previous.dme_status_detail
                    instance.dme_status_detail_updated_at = datetime.now()
            except Exception as e:
                logger.info(f"Error 515 {e}")
                pass


class DME_Files(models.Model):
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255, blank=False, null=True, default=None)
    file_path = models.TextField(max_length=1024, blank=False, null=True, default=None)
    file_type = models.CharField(max_length=16, blank=False, null=True, default=None)
    file_extension = models.CharField(
        max_length=8, blank=False, null=True, default=None
    )
    note = models.TextField(max_length=2048, blank=False, null=True, default=None)
    z_createdTimeStamp = models.DateTimeField(
        default=datetime.now, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        max_length=32, blank=False, null=True, default=None
    )

    class Meta:
        db_table = "dme_files"


class Client_Auto_Augment(models.Model):
    de_Email = models.CharField(max_length=64, blank=True, null=True, default=None)
    de_Email_Group_Emails = models.TextField(
        max_length=512, blank=True, null=True, default=None
    )
    de_To_Address_Street_1 = models.CharField(
        max_length=40, blank=True, null=True, default=None
    )
    de_To_Address_Street_2 = models.CharField(
        max_length=40, blank=True, null=True, default=None
    )
    fk_id_dme_client = models.ForeignKey(
        DME_clients, on_delete=models.CASCADE, default=3
    )
    de_to_companyName = models.CharField(
        max_length=40, blank=True, null=True, default=None
    )
    company_hours_info = models.CharField(
        max_length=40, blank=True, null=True, default=None
    )

    class Meta:
        db_table = "client_auto_augment"


class Client_Process_Mgr(models.Model):
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True, default=""
    )

    process_name = models.CharField(
        verbose_name=_("Process Name"), max_length=40, blank=False, null=True
    )

    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), default=datetime.now, blank=True, null=True
    )

    origin_puCompany = models.CharField(
        verbose_name=_("Origin PU Company"), max_length=128, blank=False, null=True
    )

    origin_pu_Address_Street_1 = models.CharField(
        verbose_name=_("Origin PU Address Street1"),
        max_length=40,
        blank=False,
        null=True,
    )

    origin_pu_Address_Street_2 = models.CharField(
        verbose_name=_("Origin PU Address Street2"),
        max_length=40,
        blank=False,
        null=True,
    )

    origin_pu_pickup_instructions_address = models.TextField(
        verbose_name=_("Origin PU instrunctions address"),
        max_length=512,
        blank=True,
        null=True,
        default="",
    )

    origin_deToCompanyName = models.CharField(
        verbose_name=_("Origin DE Company Name"),
        max_length=128,
        blank=True,
        null=True,
        default="",
    )

    origin_de_Email = models.CharField(
        verbose_name=_("Origin DE Email"),
        max_length=64,
        blank=True,
        null=True,
        default="",
    )

    origin_de_Email_Group_Emails = models.TextField(
        max_length=512, blank=True, null=True, default=None,
    )

    origin_de_To_Address_Street_1 = models.CharField(
        verbose_name=_("Origin DE Address Street 1"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )

    origin_de_To_Address_Street_2 = models.CharField(
        verbose_name=_("Origin DE Address Street 2"),
        max_length=40,
        blank=True,
        null=True,
        default="",
    )

    origin_puPickUpAvailFrom_Date = models.DateField(
        verbose_name=_("Origin PU Available From Date"),
        blank=True,
        default=None,
        null=True,
    )

    origin_pu_PickUp_Avail_Time_Hours = models.IntegerField(
        verbose_name=_("Origin PU Available Time Hours"),
        blank=True,
        default=0,
        null=True,
    )

    origin_pu_PickUp_Avail_Time_Minutes = models.IntegerField(
        verbose_name=_("Origin PU Available Time Minutes"),
        blank=True,
        default=0,
        null=True,
    )

    origin_pu_PickUp_By_Date = models.DateField(
        verbose_name=_("Origin PU By Date DME"), blank=True, null=True
    )

    origin_pu_PickUp_By_Time_Hours = models.IntegerField(
        verbose_name=_("Origin PU By Time Hours"), blank=True, default=0, null=True,
    )

    origin_pu_PickUp_By_Time_Minutes = models.IntegerField(
        verbose_name=_("Origin PU By Time Minutes"), blank=True, default=0, null=True,
    )

    class Meta:
        db_table = "client_process_mgr"


class EmailLogs(models.Model):
    id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Bookings, on_delete=models.CASCADE)
    emailName = models.CharField(max_length=255, blank=True, null=True, default=None)
    to_emails = models.CharField(max_length=255, blank=True, null=True, default=None)
    cc_emails = models.TextField(max_length=512, blank=True, null=True, default=None)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )

    class Meta:
        db_table = "email_logs"


class BookingSets(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=32, blank=True, null=True, default=None)
    booking_ids = models.TextField(blank=True, null=True, default=None)
    note = models.TextField(max_length=512, blank=True, null=True, default=None)
    status = models.CharField(max_length=255, blank=True, null=True, default=None)
    auto_select_type = models.BooleanField(
        max_length=255, blank=True, null=True, default=True
    )  # True: lowest | False: Fastest
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_booking_sets"


class Tokens(models.Model):
    id = models.AutoField(primary_key=True)
    value = models.CharField(max_length=255, default=None)
    type = models.CharField(max_length=255, default=None)
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_expiryTimeStamp = models.DateTimeField(default=None)

    class Meta:
        db_table = "tokens"


class Client_Products(models.Model):
    id = models.AutoField(primary_key=True)
    modelNumber = models.CharField(
        verbose_name=_("Model Number"), max_length=50, blank=True, null=True
    )
    e_dimUOM = models.CharField(
        verbose_name=_("Dim UOM"), max_length=10, blank=True, null=True
    )
    e_weightUOM = models.CharField(
        verbose_name=_("Weight UOM"), max_length=56, blank=True, null=True
    )
    e_dimLength = models.FloatField(verbose_name=_("Dim Length"), blank=True, null=True)
    e_dimWidth = models.FloatField(verbose_name=_("Dim Width"), blank=True, null=True)
    e_dimHeight = models.FloatField(verbose_name=_("Dim Height"), blank=True, null=True)
    e_weightPerEach = models.FloatField(
        verbose_name=_("Weight Per Each"), blank=True, null=True
    )
    fk_id_dme_client = models.ForeignKey(
        DME_clients, on_delete=models.CASCADE, blank=True, null=True
    )
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "client_products"


class Client_Ras(models.Model):
    id = models.AutoField(primary_key=True)
    ra_number = models.CharField(max_length=30, blank=True, null=True)
    dme_number = models.CharField(max_length=50, blank=True, null=True)
    name_first = models.CharField(max_length=50, blank=True, null=True)
    name_surname = models.CharField(max_length=50, blank=True, null=True)
    phone_mobile = models.CharField(max_length=30, blank=True, null=True)
    address1 = models.CharField(max_length=80, blank=True, null=True)
    address2 = models.CharField(max_length=80, blank=True, null=True)
    suburb = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=30, blank=True, null=True)
    state = models.CharField(max_length=25, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    item_model_num = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=150, blank=True, null=True)
    serial_number = models.CharField(max_length=50, blank=True, null=True)
    product_in_box = models.BooleanField(blank=True, null=True, default=False)
    fk_id_dme_client = models.ForeignKey(
        DME_clients, on_delete=models.CASCADE, blank=True, null=True
    )

    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "client_ras"


class DME_Error(models.Model):
    id = models.AutoField(primary_key=True)
    freight_provider = models.ForeignKey(Fp_freight_providers, on_delete=models.CASCADE)
    accountCode = models.CharField(max_length=32, blank=True, null=True)
    fk_booking_id = models.CharField(
        verbose_name=_("Booking ID"), max_length=64, blank=True, null=True
    )
    error_code = models.CharField(max_length=32, blank=True, null=True)
    error_description = models.TextField(max_length=500, blank=True, null=True)
    z_createdByAccount = models.CharField(
        verbose_name=_("Created by account"), max_length=64, blank=True, null=True
    )
    z_createdTimeStamp = models.DateTimeField(
        verbose_name=_("Created Timestamp"), null=True, blank=True, auto_now_add=True
    )
    z_modifiedByAccount = models.CharField(
        verbose_name=_("Modified by account"), max_length=64, blank=True, null=True
    )
    z_modifiedTimeStamp = models.DateTimeField(
        verbose_name=_("Modified Timestamp"), null=True, blank=True, auto_now=True
    )

    class Meta:
        db_table = "dme_errors"
