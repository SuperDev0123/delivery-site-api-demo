# Generated by Django 2.1.2 on 2021-08-29 16:51

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0278_auto_20210822_1525"),
    ]

    operations = [
        migrations.CreateModel(
            name="FP_status_history",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("status", models.CharField(default=None, max_length=32, null=True)),
                ("desc", models.CharField(default=None, max_length=32, null=True)),
                ("event_timestamp", models.DateTimeField(default=None, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "z_createdAt",
                    models.DateTimeField(default=django.utils.timezone.now, null=True),
                ),
            ],
        ),
        migrations.AddField(
            model_name="fp_status_history",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.Bookings"
            ),
        ),
        migrations.AddField(
            model_name="fp_status_history",
            name="fp",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="api.Fp_freight_providers",
            ),
        ),
    ]
