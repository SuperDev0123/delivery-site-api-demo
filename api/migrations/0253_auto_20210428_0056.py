# Generated by Django 2.1.2 on 2021-04-28 00:56

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0252_auto_20210423_0938"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookingsets",
            name="line_haul_date",
            field=models.DateField(
                blank=True, default=django.utils.timezone.now, null=True
            ),
        ),
        migrations.AddField(
            model_name="fp_vehicles",
            name="category",
            field=models.CharField(default=None, max_length=16, null=True),
        ),
    ]
