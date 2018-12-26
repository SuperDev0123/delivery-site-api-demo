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
	kf_staff_id = models.CharField(verbose_name=_('Staff ID'), max_length=64, blank=True, null=True, default='')
	kf_clientCustomerID_PU = models.CharField(verbose_name=_('Custom ID Pick Up'), max_length=64, blank=True, null=True, default='')
	kf_clientCustomerID_DE = models.CharField(verbose_name=_('Custom ID Deliver'), max_length=64, blank=True, null=True, default='')
	kf_Add_ID_PU = models.CharField(verbose_name=_('Add ID Pick Up'), max_length=64, blank=True, null=True, default='')
	kf_Add_ID_DE = models.CharField(verbose_name=_('Add ID Deliver'), max_length=64, blank=True, null=True, default='')
	kf_FP_ID = models.CharField(verbose_name=_('FP ID'), max_length=64, blank=True, null=True, default='')
	kf_booking_Created_For_ID = models.CharField(verbose_name=_('Booking Created For ID'), max_length=64, blank=True, null=True, default='')
	kf_email_Template = models.CharField(verbose_name=_('Email Template'), max_length=64, blank=True, null=True, default='')
	kf_Invoice_Num_Booking = models.CharField(verbose_name=_('Invoice Num Booking'), max_length=64, blank=True, null=True, default='')
	kf_booking_quote_import_id = models.CharField(verbose_name=_('Booking Quote Import ID'), max_length=64, blank=True, null=True, default='')
	kf_order_id = models.CharField(verbose_name=_('Order ID'), max_length=64, blank=True, null=True, default='')
	x_Data_Entered_Via = models.CharField(verbose_name=_('Data Entered Via'), max_length=64, blank=True, null=True, default='')
	b_booking_Priority = models.CharField(verbose_name=_('Booking Priority'), max_length=32, blank=True, null=True, default='')
	z_API_Issue = models.IntegerField(verbose_name=_('Api Issue'), blank=True, default=0)
	z_api_issue_update_flag_500 = models.BooleanField(verbose_name=_('API Issue Update Flag 500'), default=False, blank=True, null=True)
	pu_Address_Type = models.CharField(verbose_name=_('PU Address Type'), max_length=25, blank=True, null=True, default='')
	pu_Address_Street_1 = models.CharField(verbose_name=_('PU Address Street 1'), max_length=45, blank=True, null=True, default='')
	pu_Address_street_2 = models.CharField(verbose_name=_('PU Address Street 2'), max_length=45, blank=True, null=True, default='')
	pu_Address_State = models.CharField(verbose_name=_('PU Address State'), max_length=25, blank=True, null=True, default='')
	pu_Address_City = models.CharField(verbose_name=_('PU Address City'), max_length=50, blank=True, null=True, default='')
	pu_Address_Suburb = models.CharField(verbose_name=_('PU Address Suburb'), max_length=25, blank=True, null=True, default='')
	pu_Address_PostalCode = models.CharField(verbose_name=_('PU Address Postal Code'), max_length=25, blank=True, null=True, default='')
	pu_Address_Country = models.CharField(verbose_name=_('PU Address Country'), max_length=50, blank=True, null=True, default='')
	pu_Contact_F_L_Name = models.CharField(verbose_name=_('PU Contact Name'), max_length=25, blank=True, null=True, default='')
	pu_Phone_Main = models.CharField(verbose_name=_('PU Phone Main'), max_length=25, blank=True, null=True, default='')
	pu_Phone_Mobile = models.CharField(verbose_name=_('PU Phone Mobile'), max_length=25, blank=True, null=True, default='')
	pu_Email = models.CharField(verbose_name=_('PU Email'), max_length=35, blank=True, null=True, default='')
	pu_email_Group_Name = models.CharField(verbose_name=_('PU Email Group Name'), max_length=25, blank=True, null=True, default='')
	pu_email_Group = models.CharField(verbose_name=_('PU Email Group'), max_length=25, blank=True, null=True, default='')
	pu_Comm_Booking_Communicate_Via = models.CharField(verbose_name=_('PU Booking Communicate Via'), max_length=25, blank=True, null=True, default='')
	pu_Contact_FName = models.CharField(verbose_name=_('PU Contact First Name'), max_length=25, blank=True, null=True, default='')
	pu_PickUp_Instructions_Contact = models.CharField(verbose_name=_('PU Instructions Contact'), max_length=100, blank=True, null=True, default='')
	pu_WareHouse_Number = models.CharField(verbose_name=_('PU Warehouse Number'), max_length=10, blank=True, null=True, default='')
	pu_WareHouse_Bay = models.CharField(verbose_name=_('PU Warehouse Bay'), max_length=10, blank=True, null=True, default='')
	pu_Contact_Lname = models.CharField(verbose_name=_('PU Contact Last Name'), max_length=25, blank=True, null=True, default='')
	de_Email = models.CharField(verbose_name=_('DE Email'), max_length=35, blank=True, null=True, default='')
	de_To_AddressType = models.CharField(verbose_name=_('DE Address Type'), max_length=20, blank=True, null=True, default='')
	de_To_Address_Street_1 = models.CharField(verbose_name=_('DE Address Street 1'), max_length=40, blank=True, null=True, default='')
	de_To_Address_Street_2 = models.CharField(verbose_name=_('DE Address Street 2'), max_length=40, blank=True, null=True, default='')
	de_To_Address_State = models.CharField(verbose_name=_('DE Address State'), max_length=20, blank=True, null=True, default='')
	de_To_Address_City = models.CharField(verbose_name=_('DE Address City'), max_length=40, blank=True, null=True, default='')
	de_To_Address_Suburb = models.CharField(verbose_name=_('DE Address Suburb'), max_length=30, blank=True, null=True, default='')
	de_To_Address_Country = models.CharField(verbose_name=_('DE Address Country'), max_length=12, blank=True, null=True, default='')
	de_to_Contact_F_LName = models.CharField(verbose_name=_('DE Contact Name'), max_length=50, blank=True, null=True, default='')
	de_to_Contact_FName = models.CharField(verbose_name=_('DE Contact First Name'), max_length=25, blank=True, null=True, default='')
	de_to_Contact_Lname = models.CharField(verbose_name=_('DE Contact Last Name'), max_length=25, blank=True, null=True, default='')
	de_To_Comm_Delivery_Communicate_Via = models.CharField(verbose_name=_('DE Communicate Via'), max_length=40, blank=True, null=True, default='')
	de_to_Pick_Up_Instructions_Contact = models.CharField(verbose_name=_('DE Instructions Contact'), max_length=120, blank=True, null=True, default='')
	de_to_PickUp_Instructions_Address = models.CharField(verbose_name=_('DE Instructions Address'), max_length=120, blank=True, null=True, default='')
	de_to_WareHouse_Number = models.CharField(verbose_name=_('DE Warehouse Number'), max_length=30, blank=True, null=True, default='')
	de_to_WareHouse_Bay = models.CharField(verbose_name=_('DE Warehouse Bay'), max_length=25, blank=True, null=True, default='')
	de_to_Phone_Mobile = models.CharField(verbose_name=_('DE Phone Mobile'), max_length=25, blank=True, null=True, default='')
	de_to_Phone_Main = models.CharField(verbose_name=_('DE Phone Main'), max_length=30, blank=True, null=True, default='')
	de_to_addressed_Saved = models.IntegerField(verbose_name=_('DE Addressed Saved'), blank=True, default=0)
	de_Contact = models.CharField(verbose_name=_('DE Contact'), max_length=50, blank=True, null=True, default='')
	pu_PickUp_By_Date = models.DateField(verbose_name=_('PickUp By Date'), default=timezone.now, blank=True, null=True)
	pu_addressed_Saved = models.IntegerField(verbose_name=_('PU Addressed Saved'), blank=True, default=0)
	b_date_booked_by_dme = models.DateField(verbose_name=_('Date Booked By DME'), default=timezone.now, blank=True, null=True)
	b_booking_Notes = models.TextField(verbose_name=_('Booking Notes'), max_length=400, blank=True, null=True, default='')
	s_02_Booking_Cutoff_Time = models.TimeField(verbose_name=_('Booking Cutoff Time'), default=timezone.now, blank=True, null=True)
	s_05_Latest_PickUp_Date_Time_Override = models.DateTimeField(verbose_name=_('Latest PU DateTime Override'), default=timezone.now, blank=True)
	s_05_Latest_Pick_Up_Date_TimeSet = models.DateTimeField(verbose_name=_('Latest PU DateTime Set'), default=timezone.now, blank=True)
	s_06_Latest_Delivery_Date_Time_Override = models.DateTimeField(verbose_name=_('Latest DE DateTime Override'), default=timezone.now, blank=True)
	s_06_Latest_Delivery_Date_TimeSet = models.DateTimeField(verbose_name=_('Latest DE DateTime Set'), default=timezone.now, blank=True)
	s_07_PickUp_Progress = models.CharField(verbose_name=_('PU Progress'), max_length=30, blank=True, null=True, default='')
	s_08_Delivery_Progress = models.CharField(verbose_name=_('DE Progress'), max_length=30, blank=True, null=True, default='')
	s_20_Actual_Pickup_TimeStamp = models.DateTimeField(verbose_name=_('Actual PU TimeStamp'), default=timezone.now, blank=True)
	b_handling_Instructions = models.CharField(verbose_name=_('Handling Instructions'), max_length=120, blank=True, null=True, default='')
	v_price_Booking = models.IntegerField(verbose_name=_('Price Booking'), blank=True, default=0)
	v_service_Type_2 = models.CharField(verbose_name=_('Service Type 2'), max_length=30, blank=True, null=True, default='')
	b_status_API = models.CharField(verbose_name=_('Status API'), max_length=30, blank=True, null=True, default='')
	v_vehicle_Type = models.CharField(verbose_name=_('Vehicle Type'), max_length=30, blank=True, null=True, default='')
	v_customer_code = models.CharField(verbose_name=_('Customer Code'), max_length=20, blank=True, null=True, default='')
	v_service_Type_ID = models.CharField(verbose_name=_('Service Type ID'), max_length=64, blank=True, null=True, default='')
	v_service_Type = models.CharField(verbose_name=_('Service Type'), max_length=25, blank=True, null=True, default='')
	v_serviceCode_DME = models.CharField(verbose_name=_('Service Code DME'), max_length=10, blank=True, null=True, default='')
	v_service_Delivery_Days_Percentage_Days_TO_PU = models.IntegerField(verbose_name=_('Service DE days Percentage Days To PU'), blank=True, default=0)
	v_serviceTime_End = models.TimeField(verbose_name=_('Service Time End'), default=timezone.now, blank=True, null=True)
	v_serviceTime_Start = models.TimeField(verbose_name=_('Service Time Start'), default=timezone.now, blank=True, null=True)
	v_serviceDelivery_Days = models.IntegerField(verbose_name=_('Service DE Days'), blank=True, default=0)
	v_service_Delivery_Hours = models.IntegerField(verbose_name=_('Service DE Hours'), blank=True, default=0)
	v_service_DeliveryHours_TO_PU = models.IntegerField(verbose_name=_('Service DE Hours To PU'), blank=True, default=0)
	x_booking_Created_With = models.CharField(verbose_name=_('Booking Created With'), max_length=20, blank=True, null=True, default='')
	de_Email_Group_Emails = models.CharField(verbose_name=_('DE Email Group Emails'), max_length=30, blank=True, null=True, default='')
	de_Email_Group_Name = models.CharField(verbose_name=_('DE Email Group Name'), max_length=30, blank=True, null=True, default='')
	de_Options = models.CharField(verbose_name=_('DE Options'), max_length=30, blank=True, null=True, default='')
	total_lines_qty_override = models.IntegerField(verbose_name=_('Total Lines Qty Override'), blank=True, default=0)
	total_1_KG_weight_override = models.IntegerField(verbose_name=_('Total 1Kg Weight Override'), blank=True, default=0)
	total_Cubic_Meter_override = models.IntegerField(verbose_name=_('Total Cubic Meter Override'), blank=True, default=0)
	booked_for_comm_communicate_via =  models.CharField(verbose_name=_('Booked Communicate Via'), max_length=120, blank=True, null=True, default='')
	booking_Created_For = models.CharField(verbose_name=_('Booking Created For'), max_length=20, blank=True, null=True, default='')
	b_order_created = models.CharField(verbose_name=_('Order Created'), max_length=45, blank=True, null=True, default='')
	b_error_Capture = models.CharField(verbose_name=_('Error Capture'), max_length=20, blank=True, null=True, default='')
	b_error_code = models.CharField(verbose_name=_('Error Code'), max_length=20, blank=True, null=True, default='')
	b_booking_Category = models.TextField(verbose_name=_('Booking Categroy'), max_length=400, blank=True, null=True, default='')
	pu_PickUp_By_Time_Hours = models.IntegerField(verbose_name=_('PU By Time Hours'), blank=True, default=0)
	pu_PickUp_By_Time_Minutes = models.IntegerField(verbose_name=_('PU By Time Minutes'), blank=True, default=0)
	pu_PickUp_Avail_Time_Hours = models.IntegerField(verbose_name=_('PU Available Time Hours'), blank=True, default=0)
	pu_PickUp_Avail_Time_Minutes = models.IntegerField(verbose_name=_('PU Available Time Minutes'), blank=True, default=0)
	pu_PickUp_Avail_From_Date_DME = models.DateField(verbose_name=_('PU Available From Date DME'), default=timezone.now, blank=True, null=True)
	pu_PickUp_Avail_Time_Hours_DME = models.IntegerField(verbose_name=_('PU Available Time Hours DME'), blank=True, default=0)
	pu_PickUp_Avail_Time_Minutes_DME = models.IntegerField(verbose_name=_('PU Available Time Minutes DME'), blank=True, default=0)
	pu_PickUp_By_Date_DME =  models.DateField(verbose_name=_('PU By Date DME'), default=timezone.now, blank=True, null=True)
	pu_PickUp_By_Time_Hours_DME = models.IntegerField(verbose_name=_('PU By Time Hours DME'), blank=True, default=0)
	pu_PickUp_By_Time_Minutes_DME = models.IntegerField(verbose_name=_('PU By Time Minutes DME'), blank=True, default=0)
	pu_Actual_Date = models.DateField(verbose_name=_('PU Actual Date'), default=timezone.now, blank=True, null=True)
	pu_Actual_PickUp_Time = models.TimeField(verbose_name=_('Actual PU Time'), default=timezone.now, blank=True, null=True)
	de_Deliver_From_Date = models.DateField(verbose_name=_('DE From Date'), default=timezone.now, blank=True, null=True)
	de_Deliver_From_Hours = models.IntegerField(verbose_name=_('DE From Hours'), blank=True, default=0)
	de_Deliver_From_Minutes = models.IntegerField(verbose_name=_('DE From Minutes'), blank=True, default=0)
	de_Deliver_By_Date = models.DateField(verbose_name=_('DE By Date'), default=timezone.now, blank=True, null=True)
	de_Deliver_By_Hours = models.IntegerField(verbose_name=_('DE By Hours'), blank=True, default=0)
	de_Deliver_By_Minutes = models.IntegerField(verbose_name=_('De By Minutes'), blank=True, default=0)
	DME_Base_Cost = models.IntegerField(verbose_name=_('DME Base Cost'), blank=True, default=0)
	vx_Transit_Duration = models.IntegerField(verbose_name=_('Transit Duration'), blank=True, default=0)
	vx_freight_time = models.DateTimeField(verbose_name=_('Freight Time'), default=timezone.now, blank=True, null=True)
	vx_price_Booking = models.IntegerField(verbose_name=_('Price Booking'), blank=True, default=0)
	vx_price_Tax = models.IntegerField(verbose_name=_('Price Tax'), blank=True, default=0)
	vx_price_Total_Sell_Price_Override = models.IntegerField(verbose_name=_('Price Total Sell Price Override'), blank=True, default=0)
	vx_FP_ETA_Date = models.DateField(verbose_name=_('FP ETA Date'), default=timezone.now, blank=True, null=True)
	vx_FP_ETA_Time = models.TimeField(verbose_name=_('FP ETA Time'), default=timezone.now, blank=True, null=True)
	vx_service_Name_ID = models.CharField(verbose_name=_('Service Name ID'), max_length=64, blank=True, null=True, default='')
	vx_futile_Booking_Notes = models.CharField(verbose_name=_('Futile Booking Notes'), max_length=200, blank=True, null=True, default='')
	z_CreatedByAccount = models.TextField(verbose_name=_('Created By Account'), max_length=30, blank=True, null=True, default='')
	pu_Operting_Hours = models.TextField(verbose_name=_('PU Operating hours'), max_length=500, blank=True, null=True, default='')
	de_Operating_Hours = models.TextField(verbose_name=_('DE Operating hours'), max_length=500, blank=True, null=True, default='')
	z_CreatedTimestamp = models.DateTimeField(verbose_name=_('Created By Account'), default=timezone.now, blank=True, null=True)
	z_ModifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=25, blank=True, null=True, default='')
	z_ModifiedTimestamp = models.DateTimeField(verbose_name=_('Modified By Account'), default=timezone.now, blank=True, null=True)
	pu_PickUp_TimeSlot_TimeEnd = models.TimeField(verbose_name=_('PU TimeSlot TimeEnd'), default=timezone.now, blank=True, null=True)
	de_TimeSlot_TimeStart = models.TimeField(verbose_name=_('DE TimeSlot TimeStart'), default=timezone.now, blank=True, null=True)
	de_Nospecific_Time = models.IntegerField(verbose_name=_('No Specific Time'), blank=True, default=0)
	de_TimeSlot_Time_End = models.TimeField(verbose_name=_('TimeSlot Time End'), default=timezone.now, blank=True, null=True)
	de_to_TimeSlot_Date_End = models.DateField(verbose_name=_('DE to TimeSlot Date End'), default=timezone.now, blank=True, null=True)
	rec_do_not_Invoice = models.IntegerField(verbose_name=_('Rec Doc Not Invoice'), blank=True, default=0)
	b_email_Template_Name = models.CharField(verbose_name=_('Email Template Name'), max_length=30, blank=True, null=True, default='')
	pu_No_specified_Time = models.IntegerField(verbose_name=_('PU No Specific Time'), blank=True, default=0)
	notes_cancel_Booking = models.CharField(verbose_name=_('Notes Cancel Booking'), max_length=500, blank=True, null=True, default='')
	booking_Created_For_Email = models.CharField(verbose_name=_('Booking Created For Email'), max_length=35, blank=True, null=True, default='')
	z_Notes_Bugs = models.CharField(verbose_name=_('Notes Bugs'), max_length=200, blank=True, null=True, default='')
	DME_GST_Percentage = models.IntegerField(verbose_name=_('DME GST Percentage'), blank=True, default=0)
	x_ReadyStatus = models.CharField(verbose_name=_('Ready Status'), max_length=5, blank=True, null=True, default='')
	DME_Notes = models.CharField(verbose_name=_('DME Notes'), max_length=500, blank=True, null=True, default='')
	b_client_Reference_RA_Numbers_lastupdate = models.DateTimeField(verbose_name=_('Client Reference RA Number Last Update'), default=timezone.now, blank=True, null=True)
	s_04_Max_Duration_To_Delivery_Number = models.IntegerField(verbose_name=_('04 Max Duration To Delivery Number'), blank=True, default=0)
	b_client_MarkUp_PercentageOverRide = models.IntegerField(verbose_name=_('client MarkUp Percentage Override'), blank=True, default=0)
	z_admin_dme_invoice_number = models.CharField(verbose_name=_('Admin DME Invoice Number'), max_length=25, blank=True, null=True, default='')
	z_included_with_manifest_date = models.DateTimeField(verbose_name=_('Included With Manifest Date'), default=timezone.now, blank=True, null=True)
	b_dateinvoice = models.DateField(verbose_name=_('Date Invoice'), default=timezone.now, blank=True, null=True)
	b_booking_tail_lift_pickup = models.CharField(verbose_name=_('Booking Tail Lift PU'), max_length=2, blank=True, null=True, default='')
	b_booking_tail_lift_deliver = models.CharField(verbose_name=_('Booking Tail Lift DE'), max_length=2, blank=True, null=True, default='')
	b_booking_no_operator_pickup = models.IntegerField(verbose_name=_('Booking No Operator PU'), blank=True, default=0)
	b_bookingNoOperatorDeliver = models.IntegerField(verbose_name=_('Booking No Operator DE'), blank=True, default=0)
	b_ImportedFromFile = models.CharField(verbose_name=_('Imported File Filed'), max_length=30, blank=True, null=True, default='')
	b_email2_return_sent_numberofTimes = models.IntegerField(verbose_name=_('Email2 Return Sent Number Of Times'), blank=True, default=0)
	b_email1_general_sent_Number_of_times = models.IntegerField(verbose_name=_('Email1 General sent Number Of Times'), blank=True, default=0)
	b_email3_pickup_sent_numberOfTimes = models.IntegerField(verbose_name=_('Email3 PU Sent Number Of Times'), blank=True, default=0)
	b_email4_futile_sent_number_of_times = models.IntegerField(verbose_name=_('Email4 Futile Sent Number Of Times'), blank=True, default=0)
	b_send_POD_eMail = models.IntegerField(verbose_name=_('Send POD Email'), blank=True, default=0)
	b_booking_status_manual = models.CharField(verbose_name=_('Booking Status Manual'), max_length=30, blank=True, null=True, default='')
	b_booking_status_manual_DME = models.CharField(verbose_name=_('Booking Status Manual DME'), max_length=2, blank=True, null=True, default='')
	b_booking_statusmanual_DME_Note = models.CharField(verbose_name=_('Booking Status Manual DME Note'), max_length=200, blank=True, null=True, default='')
	DME_price_from_client = models.IntegerField(verbose_name=_('DME Price From Client'), blank=True, default=0)

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

class Booking_lines_data(models.Model):
	pk_id_lines_data = models.AutoField(primary_key=True)
	fk_id_booking_lines = models.CharField(verbose_name=_('FK Booking Lines Id'), max_length=64, blank=True)
	fk_booking_id = models.CharField(verbose_name=_('FK Booking Id'), max_length=64, blank=True)
	modelNumber = models.CharField(verbose_name=_('Model Number'), max_length=50, blank=True, null=True)
	itemDescription = models.TextField(verbose_name=_('Item Description'), max_length=200, blank=True, null=True)
	quantity = models.IntegerField(verbose_name=_('Quantity'), blank=True, null=True)
	itemFaultDescription = models.TextField(verbose_name=_('Item Description'), max_length=200, blank=True, null=True)
	insuranceValueEach = models.IntegerField(verbose_name=_('Insurance Value Each'), blank=True, null=True)
	gap_ra = models.TextField(verbose_name=_('Gap Ra'), max_length=300, blank=True, null=True)
	clientRefNumber = models.CharField(verbose_name=_('Client Ref Number'), max_length=50, blank=True, null=True)
	itemSerialNumbers = models.CharField(verbose_name=_('Item Serial Numbers'), max_length=100, blank=True, null=True)
	z_createdByAccount = models.CharField(verbose_name=_('Created By Account'), max_length=25, blank=True, null=True)
	z_createdTimeStamp = models.DateTimeField(verbose_name=_('Created Timestamp'), default=timezone.now, blank=True)
	z_modifiedByAccount = models.CharField(verbose_name=_('Modified By Account'), max_length=25, blank=True, null=True)
	z_modifiedTimeStamp = models.DateTimeField(verbose_name=_('Modified Timestamp'), default=timezone.now, blank=True)

	class Meta:
		db_table = 'dme_booking_lines_data'

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
