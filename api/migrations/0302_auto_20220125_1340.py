# Generated by Django 2.1.2 on 2022-01-25 13:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0301_auto_20220120_0203"),
    ]

    operations = [
        migrations.AddField(
            model_name="s_bookings",
            name="s_06_Estimated_Delivery_TimeStamp",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="s_bookings",
            name="s_21_Actual_Delivery_TimeStamp",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
