# Generated by Django 2.1.2 on 2019-11-16 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0149_auto_20191116_0732")]

    operations = [
        migrations.RemoveField(model_name="bookings", name="fp_received_date_time")
    ]
