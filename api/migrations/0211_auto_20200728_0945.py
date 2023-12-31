# Generated by Django 2.1.2 on 2020-07-28 09:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0210_auto_20200721_2335"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookings",
            name="b_bookingNoOperatorDeliver",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Booking No Operator DE",
            ),
        ),
        migrations.AlterField(
            model_name="bookings",
            name="b_booking_no_operator_pickup",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Booking No Operator PU",
            ),
        ),
    ]
