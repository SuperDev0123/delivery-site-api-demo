# Generated by Django 2.1.2 on 2019-04-24 18:18

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0061_auto_20190421_1540'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dme_status_history',
            name='depot_name',
            field=models.CharField(blank=True, default='', max_length=64, null=True, verbose_name='Depot Name'),
        ),
        migrations.AlterField(
            model_name='dme_status_history',
            name='dme_notes',
            field=models.TextField(blank=True, default='', max_length=500, null=True, verbose_name='DME notes'),
        ),
        migrations.AlterField(
            model_name='dme_status_history',
            name='event_time_stamp',
            field=models.DateTimeField(blank=True, default=datetime.datetime.now, null=True, verbose_name='Event Timestamp'),
        ),
        migrations.AlterField(
            model_name='dme_status_history',
            name='fk_fp_id',
            field=models.CharField(blank=True, default='', max_length=64, null=True, verbose_name='FP ID'),
        ),
        migrations.AlterField(
            model_name='dme_status_history',
            name='status_code_api',
            field=models.CharField(blank=True, default='', max_length=50, null=True, verbose_name='Status Code API'),
        ),
        migrations.AlterField(
            model_name='dme_status_history',
            name='status_from_api',
            field=models.CharField(blank=True, default='', max_length=50, null=True, verbose_name='Status From API'),
        ),
    ]
