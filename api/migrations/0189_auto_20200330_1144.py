# Generated by Django 2.1.2 on 2020-03-30 11:44

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0188_auto_20200327_0022"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailLogs",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "emailName",
                    models.CharField(
                        blank=True, default=None, max_length=255, null=True
                    ),
                ),
                (
                    "to_emails",
                    models.CharField(
                        blank=True, default=None, max_length=255, null=True
                    ),
                ),
                (
                    "cc_emails",
                    models.TextField(
                        blank=True, default=None, max_length=512, null=True
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
                        default=datetime.datetime.now, verbose_name="Created Timestamp"
                    ),
                ),
            ],
            options={"db_table": "email_logs",},
        ),
        migrations.AddField(
            model_name="emaillogs",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.Bookings"
            ),
        ),
    ]
