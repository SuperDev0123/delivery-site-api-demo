# Generated by Django 2.1.2 on 2020-11-14 16:00

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0216_auto_20200930_0055'),
    ]

    operations = [
        migrations.CreateModel(
            name='DME_Augment_Address',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('origin_word', models.CharField(blank=True, max_length=32, null=True)),
                ('augmented_word', models.CharField(blank=True, max_length=32, null=True)),
            ],
            options={
                'db_table': 'dme_augment_address',
            },
        ),
        migrations.CreateModel(
            name='DME_SMS_Templates',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('smsName', models.CharField(blank=True, max_length=255, null=True)),
                ('smsMessage', models.TextField(blank=True, null=True)),
                ('z_createdByAccount', models.CharField(blank=True, max_length=64, null=True, verbose_name='Created by account')),
                ('z_createdTimeStamp', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Created Timestamp')),
                ('z_modifiedByAccount', models.CharField(blank=True, max_length=64, null=True, verbose_name='Modified by account')),
                ('z_modifiedTimeStamp', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='Modified Timestamp')),
            ],
            options={
                'db_table': 'dme_sms_templates',
            },
        ),
        migrations.RenameField(
            model_name='dme_options',
            old_name='z_downloadedByAccount',
            new_name='z_modifiedByAccount',
        ),
        migrations.RemoveField(
            model_name='bok_1_headers',
            name='quote',
        ),
        migrations.AlterField(
            model_name='booking_lines',
            name='pk_booking_lines_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='bookings',
            name='api_booking_quote',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.API_booking_quotes'),
        ),
        migrations.AlterField(
            model_name='log',
            name='z_modifiedByAccount',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Modified by account'),
        ),
    ]
