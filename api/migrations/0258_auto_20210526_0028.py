# Generated by Django 2.1.2 on 2021-05-26 00:28

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0257_auto_20210512_0202"),
    ]

    operations = [
        migrations.CreateModel(
            name="FP_onforwarding",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("fp_id", models.IntegerField()),
                ("fp_company_name", models.CharField(max_length=64)),
                ("state", models.CharField(max_length=64)),
                ("postcode", models.CharField(max_length=6)),
                ("suburb", models.CharField(max_length=64)),
                ("base_price", models.FloatField()),
                ("price_per_kg", models.FloatField()),
            ],
            options={
                "db_table": "fp_onforwarding",
            },
        ),
    ]
