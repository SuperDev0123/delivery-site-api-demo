# Generated by Django 2.1.2 on 2020-12-22 00:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0228_auto_20201214_0106"),
    ]

    operations = [
        migrations.AddField(
            model_name="api_booking_quotes",
            name="is_used",
            field=models.BooleanField(default=False),
        ),
    ]