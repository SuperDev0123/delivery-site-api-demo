# Generated by Django 2.1.2 on 2018-12-14 12:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BOK_0_BookingKeys',
            fields=[
                ('pk_auto_id', models.AutoField(primary_key=True, serialize=False)),
                ('client_booking_id', models.CharField(blank=True, max_length=64, verbose_name='Client booking id')),
                ('filename', models.CharField(max_length=128, verbose_name='File name')),
                ('success', models.CharField(max_length=1, verbose_name='Success')),
                ('timestampCreated', models.DateTimeField(default=django.utils.timezone.now, verbose_name='PickUp Available From')),
                ('client', models.CharField(blank=True, max_length=64, verbose_name='Client')),
                ('v_client_pk_consigment_num', models.CharField(blank=True, max_length=64, verbose_name='Consigment num')),
                ('l_000_client_acct_number', models.IntegerField(blank=True, verbose_name='Client account number')),
                ('l_011_client_warehouse_id', models.IntegerField(blank=True, verbose_name='Client warehouse Id')),
                ('l_012_client_warehouse_name', models.CharField(blank=True, max_length=240, verbose_name='Client warehouse Name')),
            ],
        ),
        migrations.CreateModel(
            name='BOK_1_headers',
            fields=[
                ('pk_auto_id', models.AutoField(primary_key=True, serialize=False)),
                ('client_booking_id', models.CharField(blank=True, max_length=64, verbose_name='Client booking id')),
                ('b_21_b_pu_avail_from_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Available From')),
                ('b_003_b_service_name', models.CharField(blank=True, max_length=31, verbose_name='Service Name')),
                ('b_500_b_client_cust_job_code', models.CharField(blank=True, max_length=20, verbose_name='Client Job Code')),
                ('b_054_b_del_company', models.CharField(blank=True, max_length=100, verbose_name='Del company')),
                ('b_000_b_total_lines', models.IntegerField(blank=True, verbose_name='Total lines')),
                ('b_053_b_del_address_street', models.CharField(blank=True, max_length=100, verbose_name='Address street')),
                ('b_058_b_del_address_suburb', models.CharField(blank=True, max_length=40, verbose_name='Address suburb')),
                ('b_057_b_del_address_state', models.CharField(blank=True, max_length=20, verbose_name='Address state')),
                ('b_059_b_del_address_postalcode', models.IntegerField(blank=True, verbose_name='Address Postal Code')),
                ('v_client_pk_consigment_num', models.CharField(blank=True, max_length=64, verbose_name='Consigment num')),
                ('total_kg', models.FloatField(blank=True, verbose_name='Total Kg')),
            ],
        ),
        migrations.CreateModel(
            name='BOK_2_lines',
            fields=[
                ('pk_auto_id', models.AutoField(primary_key=True, serialize=False)),
                ('client_booking_id', models.CharField(blank=True, max_length=64, verbose_name='Client booking id')),
                ('l_501_client_UOM', models.CharField(blank=True, max_length=31, verbose_name='Client UOM')),
                ('l_009_weight_per_each', models.FloatField(blank=True, verbose_name='Weight per each')),
                ('l_010_totaldim', models.FloatField(blank=True, verbose_name='Totaldim')),
                ('l_500_client_run_code', models.CharField(blank=True, max_length=7, verbose_name='Client run code')),
                ('l_003_item', models.CharField(blank=True, max_length=128, verbose_name='Item')),
                ('v_client_pk_consigment_num', models.CharField(blank=True, max_length=64, verbose_name='Consigment num')),
                ('l_cubic_weight', models.FloatField(blank=True, verbose_name='Cubic Weight')),
                ('l_002_qty', models.IntegerField(blank=True, verbose_name='Address Postal Code')),
            ],
        ),
        migrations.CreateModel(
            name='Bookings',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('b_bookingID_Visual', models.CharField(blank=True, max_length=40, verbose_name='BookingID Visual')),
                ('b_dateBookedDate', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Booked Date')),
                ('puPickUpAvailFrom_Date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='PickUp Available From')),
                ('b_clientReference_RA_Numbers', models.CharField(blank=True, max_length=1000, verbose_name='Client Reference Ra Numbers')),
                ('b_status', models.CharField(blank=True, max_length=40, verbose_name='Status')),
                ('vx_freight_provider', models.CharField(blank=True, max_length=100, verbose_name='Freight Provider')),
                ('vx_serviceName', models.CharField(blank=True, max_length=50, verbose_name='Service Name')),
                ('s_05_LatestPickUpDateTimeFinal', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Lastest PickUp DateTime')),
                ('s_06_LatestDeliveryDateTimeFinal', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Latest Delivery DateTime')),
                ('v_FPBookingNumber', models.CharField(blank=True, max_length=40, verbose_name='FP Booking Number')),
                ('puCompany', models.CharField(blank=True, max_length=40, verbose_name='Company')),
                ('deToCompanyName', models.CharField(blank=True, max_length=40, verbose_name='Company Name')),
                ('consignment_label_link', models.CharField(blank=True, max_length=250, verbose_name='Consignment')),
                ('error_details', models.CharField(blank=True, default='', max_length=250, verbose_name='Error Detail')),
                ('is_printed', models.BooleanField(default=False, verbose_name='Is printed')),
            ],
        ),
        migrations.CreateModel(
            name='Client_employees',
            fields=[
                ('pk_id_client_emp', models.AutoField(primary_key=True, serialize=False)),
                ('name_last', models.CharField(max_length=30, verbose_name='last name')),
                ('name_first', models.CharField(max_length=30, verbose_name='first name')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('phone', models.IntegerField(verbose_name='phone number')),
            ],
        ),
        migrations.CreateModel(
            name='Client_warehouse',
            fields=[
                ('pk_id_client_warehouse', models.AutoField(primary_key=True, serialize=False)),
                ('warehousename', models.CharField(max_length=230, verbose_name='warehoursename')),
                ('warehouse_address1', models.TextField(verbose_name='warehouse address1')),
                ('warehouse_address2', models.TextField(verbose_name='warehouse address2')),
                ('warehouse_state', models.TextField(verbose_name='warehouse state')),
                ('warehouse_suburb', models.TextField(verbose_name='warehouse suburb')),
                ('warehouse_phone_main', models.IntegerField(verbose_name='warehouse phone number')),
                ('warehouse_hours', models.IntegerField(verbose_name='warehouse hours')),
            ],
        ),
        migrations.CreateModel(
            name='DME_clients',
            fields=[
                ('pk_id_dme_client', models.AutoField(primary_key=True, serialize=False)),
                ('company_name', models.CharField(max_length=230, verbose_name='warehoursename')),
                ('dme_account_num', models.IntegerField(verbose_name='dme account num')),
                ('phone', models.IntegerField(verbose_name='phone number')),
            ],
        ),
        migrations.CreateModel(
            name='DME_employees',
            fields=[
                ('pk_id_dme_emp', models.AutoField(primary_key=True, serialize=False)),
                ('name_last', models.CharField(max_length=30, verbose_name='last name')),
                ('name_first', models.CharField(max_length=30, verbose_name='first name')),
                ('Role', models.TextField(verbose_name='Role')),
                ('fk_id_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='client_warehouse',
            name='fk_id_dme_client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pages.DME_clients'),
        ),
        migrations.AddField(
            model_name='client_employees',
            name='fk_id_client_warehouse',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='pages.Client_warehouse'),
        ),
        migrations.AddField(
            model_name='client_employees',
            name='fk_id_dme_client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pages.DME_clients'),
        ),
        migrations.AddField(
            model_name='client_employees',
            name='fk_id_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='bookings',
            name='b_clientPU_Warehouse',
            field=models.ForeignKey(default='1', on_delete=django.db.models.deletion.CASCADE, to='pages.Client_warehouse'),
        ),
    ]
