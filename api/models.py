from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext as _
from django_base64field.fields import Base64Field
from django.contrib.auth.models import BaseUserManager

class DME_clients(models.Model):
	pk_id_dme_client = models.AutoField(primary_key=True)
	company_name = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	dme_account_num = models.IntegerField(verbose_name=_('dme account num'))
	phone = models.IntegerField(verbose_name=_('phone number'))

	class Meta:
		db_table = 'dme_clients'

class Client_warehouses(models.Model):
	pk_id_client_warehouses = models.AutoField(primary_key=True)
	fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
	warehousename = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	warehouse_address1 = models.TextField(verbose_name=_('warehouse address1'))
	warehouse_address2 = models.TextField(verbose_name=_('warehouse address2'))
	warehouse_state = models.TextField(verbose_name=_('warehouse state'))
	warehouse_suburb = models.TextField(verbose_name=_('warehouse suburb'))
	warehouse_phone_main = models.IntegerField(verbose_name=_('warehouse phone number'))
	warehouse_hours = models.IntegerField(verbose_name=_('warehouse hours'))

	class Meta:
		db_table = 'dme_client_warehouses'

class DME_employees(models.Model):
	pk_id_dme_emp = models.AutoField(primary_key=True)
	fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	Role = models.TextField(verbose_name=_('Role'))

	class Meta:
		db_table = 'dme_employees'

class Client_employees(models.Model):
	pk_id_client_emp = models.AutoField(primary_key=True)
	fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	email = models.EmailField(verbose_name=_('email address'), max_length=254, unique=True)
	phone = models.IntegerField(verbose_name=_('phone number'))
	fk_id_client_warehouses = models.OneToOneField(Client_warehouses, on_delete=models.CASCADE)

	class Meta:
		db_table = 'dme_client_employees'

class Bookings(models.Model):
	id = models.AutoField(primary_key=True)
	b_bookingID_Visual = models.CharField(verbose_name=_('BookingID Visual'), max_length=40, blank=True, null=True, default='')
	b_dateBookedDate = models.DateTimeField(verbose_name=_('Booked Date'), default=timezone.now, blank=True, null=True)
	puPickUpAvailFrom_Date = models.DateField(verbose_name=_('PickUp Available From'), default=timezone.now, blank=True, null=True)
	b_clientReference_RA_Numbers = models.CharField(verbose_name=_('Client Reference Ra Numbers'), max_length=1000, blank=True, null=True, default='')
	b_status = models.CharField(verbose_name=_('Status'), max_length=40, blank=True, null=True, default='')
	vx_freight_provider = models.CharField(verbose_name=_('Freight Provider'), max_length=100, blank=True, null=True, default='')
	vx_serviceName = models.CharField(verbose_name=_('Service Name'), max_length=50, blank=True, null=True, default='')
	s_05_LatestPickUpDateTimeFinal = models.DateTimeField(verbose_name=_('Lastest PickUp DateTime'), default=timezone.now, blank=True, null=True)
	s_06_LatestDeliveryDateTimeFinal = models.DateTimeField(verbose_name=_('Latest Delivery DateTime'), default=timezone.now, blank=True, null=True)
	v_FPBookingNumber = models.CharField(verbose_name=_('FP Booking Number'), max_length=40, blank=True, null=True, default='')
	puCompany = models.CharField(verbose_name=_('Company'), max_length=40, blank=True, null=True, default='')
	deToCompanyName = models.CharField(verbose_name=_('Company Name'), max_length=40, blank=True, null=True, default='')
	consignment_label_link = models.CharField(verbose_name=_('Consignment'), max_length=250, blank=True, null=True, default='')
	error_details = models.CharField(verbose_name=_('Error Detail'), max_length=250, blank=True, null=True, default='')
	b_clientPU_Warehouse = models.ForeignKey(Client_warehouses, on_delete=models.CASCADE, default='1')
	is_printed = models.BooleanField(verbose_name=_('Is printed'), default=False, blank=True, null=True)
	shipping_label_base64 = Base64Field(verbose_name=_('Based64 Label'), blank=True, null=True, default='')
	kf_client_id = models.CharField(verbose_name=_('KF Client ID'), max_length=64, blank=True, null=True, default='')
	b_client_name = models.CharField(verbose_name=_('Client Name'), max_length=36, blank=True, null=True, default='')
	pk_booking_id = models.CharField(verbose_name=_('Booking ID'), max_length=64, blank=True, null=True, default='')
	zb_002_client_booking_key = models.CharField(verbose_name=_('Client Booking Key'), max_length=64, blank=True, null=True, default='')
	fk_fp_pickup_id = models.CharField(verbose_name=_('KF FP pickup id'), max_length=64, blank=True, null=True, default='')
	pu_pickup_instructions_address = models.CharField(verbose_name=_('Pickup instrunctions address'), max_length=100, blank=True, null=True, default='')
	deToAddressPostalCode = models.CharField(verbose_name=_('DeliverTo Addr Postal Code'), max_length=12, blank=True, null=True, default='')

	class Meta:
		db_table = 'dme_bookings'

class Booking_lines(models.Model):
	pk_auto_id_lines = models.AutoField(primary_key=True)
	fk_booking_id = models.CharField(verbose_name=_('FK Booking Id'), max_length=64, blank=True)
	e_type_of_packaging = models.CharField(verbose_name=_('Type Of Packaging'), max_length=36, blank=True)
	e_item_type = models.CharField(verbose_name=_('Item Type'), max_length=64, blank=True)
	e_pallet_type = models.CharField(verbose_name=_('Pallet Type'), max_length=24, blank=True)
	e_item = models.CharField(verbose_name=_('Item'), max_length=56, blank=True)
	e_qty = models.IntegerField(verbose_name=_('Quantity'), blank=True, null=True)
	e_weightUOM = models.CharField(verbose_name=_('Weight UOM'), max_length=56, blank=True)
	e_weightPerEach = models.IntegerField(verbose_name=_('Weight Per Each'), blank=True, null=True)
	e_dimUOM = models.CharField(verbose_name=_('Dim UOM'), max_length=10, blank=True)
	e_dimLength = models.IntegerField(verbose_name=_('Dim Length'), blank=True, null=True)
	e_dimWidth = models.IntegerField(verbose_name=_('Dim Width'), blank=True, null=True)
	e_dimHeight = models.IntegerField(verbose_name=_('Dim Height'), blank=True, null=True)
	e_dangerousGoods = models.IntegerField(verbose_name=_('Dangerous Goods'), blank=True, null=True)
	e_insuranceValueEach = models.IntegerField(verbose_name=_('Insurance Value Each'), blank=True, null=True)
	discount_rate = models.IntegerField(verbose_name=_('Discount Rate'), blank=True, null=True)
	e_options1 = models.CharField(verbose_name=_('Option 1'), max_length=56, blank=True)
	e_options2 = models.CharField(verbose_name=_('Option 2'), max_length=56, blank=True)
	e_options3 = models.CharField(verbose_name=_('Option 3'), max_length=56, blank=True)
	e_options4 = models.CharField(verbose_name=_('Option 4'), max_length=56, blank=True)
	fk_service_id = models.CharField(verbose_name=_('Service ID'), max_length=64, blank=True)
	z_createdByAccount = models.CharField(verbose_name=_('Created By Account'), max_length=24, blank=True)
	z_documentUploadedUser = models.CharField(verbose_name=_('Document Uploaded User'), max_length=24, blank=True)
	z_modifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=24, blank=True)
	e_spec_clientRMA_Number = models.TextField(verbose_name=_('Spec ClientRMA Number'), max_length=300, blank=True)
	e_spec_customerReferenceNo = models.TextField(verbose_name=_('Spec Customer Reference No'), max_length=200, blank=True)
	taxable = models.BooleanField(verbose_name=_('Taxable'), default=False, blank=True, null=True)
	z_createdTimeStamp = models.DateTimeField(verbose_name=_('Created Timestamp'), default=timezone.now, blank=True)
	z_modifiedTimeStamp = models.DateTimeField(verbose_name=_('Modified Timestamp'), default=timezone.now, blank=True)

	class Meta:
		db_table = 'dme_booking_lines'

class BOK_0_BookingKeys(models.Model):
	pk_auto_id = models.AutoField(primary_key=True)
	client_booking_id = models.CharField(verbose_name=_('Client booking id'), max_length=64, blank=True)
	filename = models.CharField(verbose_name=_('File name'), max_length=128, blank=False)
	success = models.CharField(verbose_name=_('Success'), max_length=1)
	timestampCreated = models.DateTimeField(verbose_name=_('PickUp Available From'), default=timezone.now)
	client = models.CharField(verbose_name=_('Client'), max_length=64, blank=True)
	v_client_pk_consigment_num = models.CharField(verbose_name=_('Consigment num'), max_length=64, blank=True)
	l_000_client_acct_number = models.IntegerField(verbose_name=_('Client account number'), blank=True)
	l_011_client_warehouse_id = models.IntegerField(verbose_name=_('Client warehouse Id'), blank=True)
	l_012_client_warehouse_name = models.CharField(verbose_name=_('Client warehouse Name'), max_length=240, blank=True)

	class Meta:
		db_table = 'bok_0_bookingkeys'

class BOK_1_headers(models.Model):
	pk_auto_id = models.AutoField(primary_key=True)
	client_booking_id = models.CharField(verbose_name=_('Client booking id'), max_length=64, blank=True)
	b_21_b_pu_avail_from_date = models.DateTimeField(verbose_name=_('Available From'), default=timezone.now)
	b_003_b_service_name = models.CharField(verbose_name=_('Service Name'), max_length=31, blank=True)
	b_500_b_client_cust_job_code = models.CharField(verbose_name=_('Client Job Code'), max_length=20, blank=True)
	b_054_b_del_company = models.CharField(verbose_name=_('Del company'), max_length=100, blank=True)
	b_000_b_total_lines = models.IntegerField(verbose_name=_('Total lines'), blank=True)
	b_053_b_del_address_street = models.CharField(verbose_name=_('Address street'), max_length=100, blank=True)
	b_058_b_del_address_suburb = models.CharField(verbose_name=_('Address suburb'), max_length=40, blank=True)
	b_057_b_del_address_state = models.CharField(verbose_name=_('Address state'), max_length=20, blank=True)
	b_059_b_del_address_postalcode = models.IntegerField(verbose_name=_('Address Postal Code'), blank=True)
	v_client_pk_consigment_num = models.CharField(verbose_name=_('Consigment num'), max_length=64, blank=True)
	total_kg = models.FloatField(verbose_name=_('Total Kg'), blank=True)
	success = models.CharField(verbose_name=_('Success'), max_length=1, default=0)

	class Meta:
		db_table = 'bok_1_headers'

class BOK_2_lines(models.Model):
	pk_auto_id = models.AutoField(primary_key=True)
	client_booking_id = models.CharField(verbose_name=_('Client booking id'), max_length=64, blank=True, null=True)
	l_501_client_UOM = models.CharField(verbose_name=_('Client UOM'), max_length=31, blank=True, null=True)
	l_009_weight_per_each = models.FloatField(verbose_name=_('Weight per each'), blank=True, null=True)
	l_010_totaldim = models.FloatField(verbose_name=_('Totaldim'), blank=True, null=True)
	l_500_client_run_code = models.CharField(verbose_name=_('Client run code'), max_length=7, blank=True, null=True)
	l_003_item = models.CharField(verbose_name=_('Item'), max_length=128, blank=True, null=True)
	v_client_pk_consigment_num = models.CharField(verbose_name=_('Consigment num'), max_length=64, blank=True, null=True)
	l_cubic_weight = models.FloatField(verbose_name=_('Cubic Weight'), blank=True, null=True)
	l_002_qty = models.IntegerField(verbose_name=_('Address Postal Code'), blank=True, null=True)
	success = models.CharField(verbose_name=_('Success'), max_length=1, default=0, blank=True, null=True)

	class Meta:
		db_table = 'bok_2_lines'

class BOK_3_lines_data(models.Model):
	pk_auto_id = models.AutoField(primary_key=True)
	client_booking_id = models.CharField(verbose_name=_('Client booking id'), max_length=64, blank=True, null=True)
	fk_booking_id = models.CharField(verbose_name=_('FK Booking Id'), max_length=64, blank=True)
	v_client_pk_consigment_num = models.CharField(verbose_name=_('Consigment num'), max_length=64, blank=True, null=True)
	ld_001_qty = models.IntegerField(verbose_name=_('Quantity'), blank=True, null=True)
	ld_002_model_number = models.CharField(verbose_name=_('Consigment num'), max_length=40, blank=True, null=True)
	ld_003_item_description = models.TextField(verbose_name=_('Item Description'), max_length=500, blank=True, null=True)
	ld_004_fault_description = models.CharField(verbose_name=_('fault Description'), max_length=500, blank=True, null=True)
	ld_005_item_serial_number = models.CharField(verbose_name=_('Item Serial Number'), max_length=40, blank=True, null=True)
	ld_006_insurance_value = models.IntegerField(verbose_name=_('Insurance Value'), blank=True, null=True)
	ld_007_gap_ra = models.TextField(verbose_name=_('Gap Ra'), max_length=300, blank=True, null=True)
	ld_008_client_ref_number = models.CharField(verbose_name=_('Client Ref Number'), max_length=40, blank=True, null=True)
	z_createdByAccount = models.CharField(verbose_name=_('Created By Account'), max_length=25, blank=True, null=True)
	z_createdTimeStamp = models.DateTimeField(verbose_name=_('Created Timestamp'), default=timezone.now, blank=True)
	z_modifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=25, blank=True, null=True)
	z_modifiedTimeStamp = models.DateTimeField(verbose_name=_('Modified Timestamp'), default=timezone.now, blank=True)

	class Meta:
		db_table = 'bok_3_lines_data'

class Booking_Status_History(models.Model):
	id = models.AutoField(primary_key=True)
	fk_booking_id = models.ForeignKey(Bookings, on_delete=models.CASCADE, default='1')
	status_from_api = models.CharField(verbose_name=_('Status From API'), max_length=32, blank=True, default='')
	status_date = models.DateTimeField(verbose_name=_('Status Date'), default=timezone.now, blank=True)
	notes = models.TextField(verbose_name=_('Notes'), max_length=500, blank=True, null=True, default='')
	status_date_modified = models.DateTimeField(verbose_name=_('Status Date'), default=timezone.now, blank=True)
	status_code = models.CharField(verbose_name=_('Status code'), max_length=20, blank=True, default='')
	z_createdBy = models.CharField(verbose_name=_('Created By'), max_length=40, blank=True, default='')
	z_createdByAccount = models.CharField(verbose_name=_('Created By Account'), max_length=40, blank=True, default='')
	z_createdTimeStamp = models.DateTimeField(verbose_name=_('Created Timestamp'), default=timezone.now, blank=True)
	z_modifiedBy = models.CharField(verbose_name=_('Modified By'), max_length=40, blank=True, default='')
	z_modifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=40, blank=True, default='')
	z_modifiedTimeStamp = models.DateTimeField(verbose_name=_('Modified Timestamp'), default=timezone.now, blank=True)
	status_preTranslation = models.CharField(verbose_name=_('Status Pre-translation'), max_length=30, blank=True, null=True, default='')
	pod_signed_by = models.CharField(verbose_name=_('Pod Signed By'), max_length=30, blank=True, null=True, default='')
	Responsible_Person = models.CharField(verbose_name=_('Responsible Person'), max_length=40, blank=True, null=True, default='')
	updateViaAPI = models.DateTimeField(verbose_name=_('Updated via API'), default=timezone.now, blank=True)
	fk_fpID = models.CharField(verbose_name=_('FP ID'), max_length=36, blank=True, default='')
	freightProvider = models.CharField(verbose_name=_('Freight Provider'), max_length=30, blank=True, default='')
	status_api = models.CharField(verbose_name=_('Status API'), max_length=40, blank=True, default='')
	depotName = models.CharField(verbose_name=_('Depot Name'), max_length=30, blank=True, default='')

	class Meta:
		db_table = 'dme_booking_status_history'

class Log(models.Model):
	id = models.AutoField(primary_key=True)
	fk_booking_id = models.ForeignKey(Bookings, on_delete=models.CASCADE, default='1')
	request_payload = models.TextField(verbose_name=_('Request Payload'), max_length=2000, blank=True, default='')
	response = models.TextField(verbose_name=_('Response'), max_length=10000, blank=True, default='')
	request_timestamp = models.DateTimeField(verbose_name=_('Request Timestamp'), default=timezone.now, blank=True)
	request_status = models.CharField(verbose_name=_('Request Status'), max_length=20, blank=True, default='')
	request_type = models.CharField(verbose_name=_('Request Type'), max_length=30, blank=True, default='')
	fk_service_provider_id = models.CharField(verbose_name=_('Service Provider ID'), max_length=36, blank=True, default='')
	z_createdBy = models.CharField(verbose_name=_('Created By'), max_length=40, blank=True, default='')
	z_createdByAccount = models.CharField(verbose_name=_('Created By Account'), max_length=40, blank=True, default='')
	z_createdTimeStamp = models.DateTimeField(verbose_name=_('Created Timestamp'), default=timezone.now, blank=True)
	z_modifiedBy = models.CharField(verbose_name=_('Modified By'), max_length=40, blank=True, default='')
	z_modifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=40, blank=True, default='')
	z_modifiedTimeStamp = models.DateTimeField(verbose_name=_('Modified Timestamp'), default=timezone.now, blank=True)

	class Meta:
		db_table = 'dme_log'
