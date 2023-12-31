# Generated by Django 2.1.2 on 2020-06-16 02:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0204_auto_20200616_0222"),
    ]

    operations = [
        migrations.CreateModel(
            name="Client_Products",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "modelNumber",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        null=True,
                        verbose_name="Model Number",
                    ),
                ),
                (
                    "e_dimUOM",
                    models.CharField(
                        blank=True, max_length=10, null=True, verbose_name="Dim UOM"
                    ),
                ),
                (
                    "e_weightUOM",
                    models.CharField(
                        blank=True, max_length=56, null=True, verbose_name="Weight UOM"
                    ),
                ),
                (
                    "e_dimLength",
                    models.FloatField(blank=True, null=True, verbose_name="Dim Length"),
                ),
                (
                    "e_dimWidth",
                    models.FloatField(blank=True, null=True, verbose_name="Dim Width"),
                ),
                (
                    "e_dimHeight",
                    models.FloatField(blank=True, null=True, verbose_name="Dim Height"),
                ),
                (
                    "e_weightPerEach",
                    models.FloatField(
                        blank=True, null=True, verbose_name="Weight Per Each"
                    ),
                ),
                (
                    "z_createdByAccount",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        verbose_name="Created by account",
                    ),
                ),
                (
                    "z_createdTimeStamp",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created Timestamp"
                    ),
                ),
                (
                    "z_modifiedByAccount",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        verbose_name="Modified by account",
                    ),
                ),
                (
                    "z_modifiedTimeStamp",
                    models.DateTimeField(
                        auto_now=True, null=True, verbose_name="Modified Timestamp"
                    ),
                ),
                (
                    "fk_id_dme_client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.DME_clients",
                    ),
                ),
            ],
            options={"db_table": "client_products",},
        ),
        migrations.AlterField(
            model_name="bookings",
            name="api_booking_quote",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.API_booking_quotes",
            ),
        ),
    ]
