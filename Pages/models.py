from django.db import models
from django.utils import timezone
# Create your models here.
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
	fk_id_dme_client = models.OneToOneField(DME_clients, on_delete=models.CASCADE)
	warehoursename = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
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
	booking_id = models.CharField(verbose_name=_('booking id'), max_length=230, blank=False)
	qty = models.IntegerField(verbose_name=_('qty'))
	booked_date = models.DateTimeField(verbose_name=_('booked date'), default=timezone.now)
	pickup_from_date = models.DateTimeField(verbose_name=_('pickup from date'), default=timezone.now)
	ref_number = models.IntegerField(verbose_name=_('ref number'))
	status = models.CharField(verbose_name=_('status'), max_length=230)
	freight_provider = models.CharField(verbose_name=_('freight provider'), max_length=30)
	service = models.CharField(verbose_name=_('service'), max_length=230)
	pickup_by = models.CharField(verbose_name=_('pickup by'), max_length=230)
	latest_delivery = models.CharField(verbose_name=_('latest devlivery'), max_length=230)
	consignment = models.CharField(verbose_name=_('consignment'), max_length=230)
	pick_up_entity = models.CharField(verbose_name=_('booking id'), max_length=230)
	delivery_entity = models.CharField(verbose_name=_('booking id'), max_length=230)




