# Generated by Django 2.1.2 on 2019-05-20 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0091_auto_20190520_1952'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookings',
            name='rpt_pod_from_file_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bookings',
            name='rpt_proof_of_del_from_csv_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
