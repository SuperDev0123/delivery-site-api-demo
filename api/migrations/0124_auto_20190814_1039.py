# Generated by Django 2.1.2 on 2019-08-14 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0123_auto_20190814_1027")]

    operations = [
        migrations.RemoveField(
            model_name="bok_1_headers", name="b_000_3_consignment_nuumber"
        ),
        migrations.AddField(
            model_name="bok_1_headers",
            name="b_000_3_consignment_number",
            field=models.CharField(blank=True, default="", max_length=32, null=True),
        ),
    ]
