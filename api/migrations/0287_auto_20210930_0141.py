# Generated by Django 2.1.2 on 2021-09-30 01:41

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0286_auto_20210927_0253"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookings",
            name="inv_booked_quoted",
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]
