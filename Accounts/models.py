from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.conf import settings

class DME_employees(models.Model):
	__pk_id_dme_emp = models.AutoField(primary_key=True)
	_fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	Role = models.TextField(verbose_name=_('Role'))

class Client_employees(models.Model):
	__pk_id_client_emp = models.AutoField(primary_key=True)
	_fk_id_user = models.ForeignKey(settings.AUTH_USER_MODEL)
	_fk_id_dme_client = models.OneToOneField(DME_clients, on_delete=models.CASCADE, primary_key=True)
	name_last = models.CharField(verbose_name=_('last name'), max_length=30, blank=False)
	name_first = models.CharField(verbose_name=_('first name'), max_length=30, blank=False)
	email = models.EmailField(verbose_name=_('email address'), max_length=254, unique=True)
	phone = models.IntegerField(verbose_name=_('phone number'))

	_fk_id_client_warehouse = models.OneToOneField(Client_Warehouse, on_delete=models.CASCADE, primary_key=True)


class Client_Warehouse(models.Model):
	__pk_id_client_warehouse = models.AutoField(primary_key=True)
	_fk_id_dme_client = models.OneToOneField(DME_clients, on_delete=models.CASCADE, primary_key=True)
	warehoursename = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	warehouse_address1 = models.TextField(verbose_name=_('warehouse address1'))
	warehouse_address2 = models.TextField(verbose_name=_('warehouse address2'))
	warehouse_state = models.TextField(verbose_name=_('warehouse state'))
	warehouse_suburb = models.TextField(verbose_name=_('warehouse suburb'))
	warehouse_phone_main = models.IntegerField(verbose_name=_('warehouse phone number'))		
	#warehouse_hours = models.DateTimeField(verbose_name=_('warehouse hours'), default=timezone.now)
	warehouse_hours = models.IntegerField(verbose_name=_('warehouse hours'))

class DME_clients(modesl.Model):
	__pk_id_dme_client = models.AutoField(primary_key=True)
	company_name = models.CharField(verbose_name=_('warehoursename'), max_length=230, blank=False)
	dme_account_num = models.IntegerField(verbose_name=_('dme account num'))
	phone = models.IntegerField(verbose_name=_('phone number'))
		