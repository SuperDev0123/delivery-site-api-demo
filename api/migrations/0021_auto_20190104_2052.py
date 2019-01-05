# Generated by Django 2.1.2 on 2019-01-04 20:52

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_auto_20190104_2043'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookings',
            name='de_TimeSlot_TimeStart',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='DE TimeSlot TimeStart'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='de_TimeSlot_Time_End',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='TimeSlot Time End'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='pu_Actual_PickUp_Time',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Actual PU Time'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='pu_PickUp_TimeSlot_TimeEnd',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='PU TimeSlot TimeEnd'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='s_02_Booking_Cutoff_Time',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Booking Cutoff Time'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='v_serviceTime_End',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Service Time End'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='v_serviceTime_Start',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Service Time Start'),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='vx_FP_ETA_Time',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='FP ETA Time'),
        ),
    ]
