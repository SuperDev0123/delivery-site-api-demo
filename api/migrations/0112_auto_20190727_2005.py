# Generated by Django 2.1.2 on 2019-07-27 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0111_auto_20190724_0406")]

    operations = [
        migrations.AddField(
            model_name="utl_dme_status",
            name="dme_status_label",
            field=models.CharField(blank=True, max_length=128, null=True),
        )
    ]
