# Generated by Django 2.1.2 on 2023-02-23 00:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0341_auto_20230205_1122"),
    ]

    operations = [
        migrations.AddField(
            model_name="bok_1_headers",
            name="b_095_authority_to_leave",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]