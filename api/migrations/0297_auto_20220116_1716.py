# Generated by Django 2.1.2 on 2022-01-16 17:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0296_auto_20220110_0152"),
    ]

    operations = [
        migrations.CreateModel(
            name="DMEBookingCSNote",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("note", models.TextField()),
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
            ],
            options={
                "db_table": "dme_booking_cs_note",
            },
        ),
        migrations.AddField(
            model_name="dmebookingcsnote",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.Bookings"
            ),
        ),
    ]
