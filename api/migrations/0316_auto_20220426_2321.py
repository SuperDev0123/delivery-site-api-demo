# Generated by Django 2.1.2 on 2022-04-26 23:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0315_auto_20220425_0554"),
    ]

    operations = [
        migrations.AddField(
            model_name="dme_manifest_log",
            name="need_truck",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
