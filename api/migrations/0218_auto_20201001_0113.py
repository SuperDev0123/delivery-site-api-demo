# Generated by Django 2.1.2 on 2020-10-01 01:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0217_auto_20201001_0108"),
    ]

    operations = [
        migrations.AddField(
            model_name="client_products",
            name="qty",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
