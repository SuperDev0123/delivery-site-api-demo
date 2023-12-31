# Generated by Django 2.1.2 on 2019-03-03 21:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_auto_20190301_1840'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dme_log_addr',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('addresses', models.TextField(blank=True, default='', null=True, verbose_name='Address Info')),
                ('fk_booking_id', models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='Description')),
                ('consignmentNumber', models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='Consignment Number')),
                ('length', models.FloatField(blank=True, default=0, null=True, verbose_name='Length')),
                ('width', models.FloatField(blank=True, default=0, null=True, verbose_name='Width')),
                ('height', models.FloatField(blank=True, default=0, null=True, verbose_name='Height')),
                ('weight', models.FloatField(blank=True, default=0, null=True, verbose_name='Height')),
            ],
            options={
                'db_table': 'dme_log_addr',
            },
        ),
    ]
