# Generated by Django 2.1.2 on 2022-01-19 00:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0297_auto_20220116_1716"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bok_1_headers",
            name="b_021_b_pu_avail_from_date",
            field=models.DateField(
                blank=True, default=None, null=True, verbose_name="Available From"
            ),
        ),
    ]
