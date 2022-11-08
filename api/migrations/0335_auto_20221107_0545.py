# Generated by Django 2.1.2 on 2022-11-07 05:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0334_auto_20221021_1407"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking_lines_data",
            name="packed_status",
            field=models.CharField(
                choices=[
                    ("original", "original"),
                    ("auto", "auto"),
                    ("manual", "manual"),
                    ("scanned", "scanned"),
                ],
                default=None,
                max_length=16,
                null=True,
            ),
        )
    ]
