# Generated by Django 2.1.2 on 2021-03-19 02:59

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0245_auto_20210318_1303"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bok_1_headers",
            old_name="b_074_b_pu_delivery_access",
            new_name="b_074_b_pu_access",
        ),
        migrations.RenameField(
            model_name="bok_1_headers",
            old_name="b_075_b_del_delivery_access",
            new_name="b_075_b_del_access",
        ),
    ]