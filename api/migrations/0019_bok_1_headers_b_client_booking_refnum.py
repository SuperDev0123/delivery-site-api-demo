# Generated by Django 2.1.2 on 2019-02-24 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_remove_bok_1_headers_b_client_booking_ref_num'),
    ]

    operations = [
        migrations.AddField(
            model_name='bok_1_headers',
            name='b_client_booking_refnum',
            field=models.CharField(blank=True, default='', max_length=64, null=True),
        ),
    ]
