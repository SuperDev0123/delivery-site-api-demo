# Generated by Django 2.1.2 on 2020-12-14 01:06

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0227_auto_20201209_0208"),
    ]

    operations = [
        migrations.CreateModel(
            name="FC_Log",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("client_booking_id", models.CharField(max_length=64)),
                (
                    "z_createdTimeStamp",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        null=True,
                        verbose_name="Created Timestamp",
                    ),
                ),
                (
                    "new_quote",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="api.API_booking_quotes",
                    ),
                ),
                (
                    "old_quote",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="api.API_booking_quotes",
                    ),
                ),
            ],
            options={
                "db_table": "fc_log",
            },
        ),
    ]