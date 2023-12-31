# Generated by Django 2.1.2 on 2021-01-25 02:33

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0234_auto_20210113_0007"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingCostOption",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(default=True)),
                ("amount", models.FloatField(default=0, null=True)),
                ("is_percentage", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "dme_booking_cost_options",
            },
        ),
        migrations.CreateModel(
            name="CostOption",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(default=None, max_length=16, null=True)),
                (
                    "description",
                    models.CharField(default=None, max_length=64, null=True),
                ),
            ],
            options={
                "db_table": "dme_cost_options",
            },
        ),
        migrations.CreateModel(
            name="CostOptionMap",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "fp_cost_option",
                    models.CharField(default=None, max_length=128, null=True),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("amount", models.FloatField(default=0, null=True)),
                ("is_percentage", models.BooleanField(default=False)),
                (
                    "dme_cost_option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.CostOption"
                    ),
                ),
                (
                    "fp",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.Fp_freight_providers",
                    ),
                ),
            ],
            options={
                "db_table": "dme_utl_map_fp_cost_options",
            },
        ),
        migrations.AddField(
            model_name="bookingcostoption",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.Bookings"
            ),
        ),
        migrations.AddField(
            model_name="bookingcostoption",
            name="cost_option",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.CostOption"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="bookingcostoption",
            unique_together={("booking", "cost_option")},
        ),
    ]
