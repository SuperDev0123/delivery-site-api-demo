from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from pages.models import Bookings

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