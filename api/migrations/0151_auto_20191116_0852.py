# Generated by Django 2.1.2 on 2019-11-16 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0150_auto_20191116_0803")]

    operations = [
        migrations.RenameField(
            model_name="bookings",
            old_name="z_first_scan_label_date",
            new_name="fp_received_date_time",
        )
    ]
