# Generated by Django 2.1.2 on 2018-12-14 16:39

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0006_auto_20181214_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookings',
            name='b_dateBookedDate',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Booked Date'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='is_printed',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Is printed'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='puPickUpAvailFrom_Date',
            field=models.DateField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='PickUp Available From'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='s_05_LatestPickUpDateTimeFinal',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Lastest PickUp DateTime'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='s_06_LatestDeliveryDateTimeFinal',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Latest Delivery DateTime'),
        ),
    ]
