# Generated by Django 2.1.2 on 2020-10-05 01:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0218_auto_20201001_0113"),
    ]

    operations = [
        migrations.AddField(
            model_name="dme_clients",
            name="client_customer_mark_up",
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]