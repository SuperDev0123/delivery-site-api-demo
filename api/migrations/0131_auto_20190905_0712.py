# Generated by Django 2.1.2 on 2019-09-05 07:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0130_auto_20190903_0033")]

    operations = [
        migrations.AddField(
            model_name="bookings",
            name="x_manual_booked_flag",
            field=models.BooleanField(blank=True, default=False, null=True),
        )
    ]
