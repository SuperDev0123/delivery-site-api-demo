# Generated by Django 2.1.2 on 2020-02-10 23:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0172_auto_20200210_2305"),
    ]

    operations = [
        migrations.RenameField(
            model_name="fp_pricing_rules",
            old_name="serivce_type",
            new_name="service_type",
        ),
    ]
