# Generated by Django 2.1.2 on 2021-04-01 01:02

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0247_auto_20210331_0129"),
    ]

    operations = [
        migrations.AddField(
            model_name="bok_2_lines",
            name="is_deleted",
            field=models.BooleanField(default=False, null=True),
        )
    ]
