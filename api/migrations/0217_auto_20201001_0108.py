# Generated by Django 2.1.2 on 2020-10-01 01:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0216_auto_20201001_0057"),
    ]

    operations = [
        migrations.AddField(
            model_name="client_products",
            name="description",
            field=models.CharField(
                blank=True, default=None, max_length=1024, null=True
            ),
        ),
    ]