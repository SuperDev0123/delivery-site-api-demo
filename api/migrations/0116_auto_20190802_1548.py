# Generated by Django 2.1.2 on 2019-08-02 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0115_auto_20190802_1540")]

    operations = [
        migrations.AddField(
            model_name="bookings",
            name="vx_freight_provider_carrier",
            field=models.CharField(blank=True, default=None, max_length=32, null=True),
        )
    ]
