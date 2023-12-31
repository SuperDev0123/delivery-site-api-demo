# Generated by Django 2.1.2 on 2021-01-05 00:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0229_auto_20201222_0016"),
    ]

    operations = [
        migrations.AlterField(
            model_name="log",
            name="fk_service_provider_id",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=36,
                null=True,
                verbose_name="Service Provider ID",
            ),
        ),
    ]
