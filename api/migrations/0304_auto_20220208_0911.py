# Generated by Django 2.1.2 on 2022-02-08 09:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0303_auto_20220202_0603"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookings",
            name="inv_billing_status_note",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="bookingsets",
            name="name",
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
    ]
