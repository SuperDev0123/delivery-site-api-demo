# Generated by Django 2.1.2 on 2020-02-10 03:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0169_auto_20200210_0257"),
    ]

    operations = [
        migrations.AddField(
            model_name="fp_pricing_rules",
            name="both_way",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
