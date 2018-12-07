from django.db import models
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from django.conf import settings
from django.utils.translation import gettext as _

class DME_clients(models.Model):
	pk_id_dme_client = models.AutoField(primary_key=True)
	company_name = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	dme_account_num = models.IntegerField(verbose_name=_('dme account num'))
	phone = models.IntegerField(verbose_name=_('phone number'))

class Client_Warehouse(models.Model):
	pk_id_client_warehouse = models.AutoField(primary_key=True)
	fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
	warehousename = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	warehouse_address1 = models.TextField(verbose_name=_('warehouse address1'))
	warehouse_address2 = models.TextField(verbose_name=_('warehouse address2'))
	warehouse_state = models.TextField(verbose_name=_('warehouse state'))
	warehouse_suburb = models.TextField(verbose_name=_('warehouse suburb'))
	warehouse_phone_main = models.IntegerField(verbose_name=_('warehouse phone number'))		
	#warehouse_hours = models.DateTimeField(verbose_name=_('warehouse hours'), default=timezone.now)
	warehouse_hours = models.IntegerField(verbose_name=_('warehouse hours'))

class DME_employees(models.Model):
	pk_id_dme_emp = models.AutoField(primary_key=True)
	fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	Role = models.TextField(verbose_name=_('Role'))

class Client_employees(models.Model):
	pk_id_client_emp = models.AutoField(primary_key=True)
	fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	fk_id_dme_client = models.ForeignKey(DME_clients, on_delete=models.CASCADE)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	email = models.EmailField(verbose_name=_('email address'), max_length=254, unique=True)
	phone = models.IntegerField(verbose_name=_('phone number'))
	fk_id_client_warehouse = models.OneToOneField(Client_Warehouse, on_delete=models.CASCADE)

class bookings(models.Model):
	id = models.AutoField(primary_key=True)
	b_bookingID_Visual = models.CharField(verbose_name=_('BookingID Visual'), max_length=40, blank=True)
	b_dateBookedDate = models.DateTimeField(verbose_name=_('Booked Date'), default=timezone.now)
	puPickUpAvailFrom_Date = models.DateTimeField(verbose_name=_('PickUp Available From'), default=timezone.now)
	b_clientReference_RA_Numbers = models.CharField(verbose_name=_('Client Reference Ra Numbers'), max_length=1000, blank=True)
	b_status = models.CharField(verbose_name=_('Status'), max_length=40, blank=True)
	vx_freight_provider = models.CharField(verbose_name=_('Freight Provider'), max_length=100, blank=True)
	vx_serviceName = models.CharField(verbose_name=_('Service Name'), max_length=50, blank=True)
	s_05_LatestPickUpDateTimeFinal = models.DateTimeField(verbose_name=_('Lastest PickUp DateTime'), default=timezone.now)
	s_06_LatestDeliveryDateTimeFinal = models.DateTimeField(verbose_name=_('Latest Delivery DateTime'), default=timezone.now)
	v_FPBookingNumber = models.CharField(verbose_name=_('FP Booking Number'), max_length=40, blank=True)
	puCompany = models.CharField(verbose_name=_('Company'), max_length=40, blank=True)
	deToCompanyName = models.CharField(verbose_name=_('Company Name'), max_length=40, blank=True)
	consignment_label_link = models.CharField(verbose_name=_('Consignment'), max_length=250, blank=True)
	error_details = models.CharField(verbose_name=_('Error Detail'), max_length=250, blank=True, default='')
	b_clientPU_Warehouse = models.ForeignKey(Client_Warehouse, on_delete=models.CASCADE, default='1')