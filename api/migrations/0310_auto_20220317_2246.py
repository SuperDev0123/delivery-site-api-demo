# Generated by Django 2.1.2 on 2022-03-17 22:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0309_auto_20220316_0242"),
    ]

    operations = [
        migrations.AddField(
            model_name="fp_vehicles",
            name="max_cbm",
            field=models.FloatField(default=None, null=True),
        ),
    ]