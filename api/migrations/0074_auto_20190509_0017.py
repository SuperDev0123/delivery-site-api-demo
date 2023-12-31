# Generated by Django 2.1.2 on 2019-05-09 00:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0073_auto_20190507_1639'),
    ]

    operations = [
        migrations.AddField(
            model_name='api_booking_confirmation_lines',
            name='fp_event_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='api_booking_confirmation_lines',
            name='fp_event_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='api_booking_confirmation_lines',
            name='fp_scan_data',
            field=models.CharField(blank=True, default='', max_length=64, null=True),
        ),
    ]
