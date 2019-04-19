# Generated by Django 2.1.2 on 2019-04-19 23:21

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0058_auto_20190419_1751'),
    ]

    operations = [
        migrations.CreateModel(
            name='Utl_dme_status',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('phone', models.IntegerField(blank=True, null=True, verbose_name='phone number')),
                ('dme_delivery_status_category', models.CharField(blank=True, max_length=64, null=True)),
                ('dme_delivery_status', models.CharField(blank=True, max_length=64, null=True)),
                ('dev_notes', models.TextField(blank=True, max_length=400, null=True)),
                ('z_createdByAccount', models.CharField(blank=True, max_length=64, null=True, verbose_name='Created by account')),
                ('z_createdTimeStamp', models.DateTimeField(default=datetime.datetime.now, verbose_name='Created Timestamp')),
                ('z_modifiedByAccount', models.CharField(blank=True, max_length=64, null=True, verbose_name='Modified by account')),
                ('z_modifiedTimeStamp', models.DateTimeField(default=datetime.datetime.now, verbose_name='Modified Timestamp')),
            ],
            options={
                'db_table': 'utl_dme_status',
            },
        ),
        migrations.AddField(
            model_name='dme_status_history',
            name='dme_notes',
            field=models.TextField(blank=True, default='', max_length=500, verbose_name='DME notes'),
        ),
    ]
