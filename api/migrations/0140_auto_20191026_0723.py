# Generated by Django 2.1.2 on 2019-10-26 07:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0139_auto_20191021_0056")]

    operations = [
        migrations.AddField(
            model_name="dme_utl_fp_statuses",
            name="fp_status_description",
            field=models.TextField(blank=True, default="", max_length=1024, null=True),
        )
    ]
