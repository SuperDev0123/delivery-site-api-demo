# Generated by Django 2.1.2 on 2022-02-02 06:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0302_auto_20220125_1340"),
    ]

    operations = [
        migrations.AddField(
            model_name="s_bookings",
            name="b_client_booking_ref_num",
            field=models.CharField(blank=True, default=None, max_length=64, null=True),
        ),
    ]
