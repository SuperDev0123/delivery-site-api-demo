# Generated by Django 2.1.2 on 2021-08-04 03:01

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0274_merge_20210726_0747"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking_lines",
            name="zbl_131_decimal_1",
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]