# Generated by Django 2.1.2 on 2019-12-02 01:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("api", "0155_auto_20191125_0907")]

    operations = [
        migrations.AddField(
            model_name="bookings",
            name="dme_status_detail_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bookings",
            name="dme_status_detail_updated_by",
            field=models.CharField(blank=True, default="", max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="bookings",
            name="prev_dme_status_detail",
            field=models.CharField(blank=True, default="", max_length=255, null=True),
        ),
    ]
