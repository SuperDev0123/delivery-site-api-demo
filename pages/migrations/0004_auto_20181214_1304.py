# Generated by Django 2.1.2 on 2018-12-14 13:04

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0003_auto_20181214_1237'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookings',
            name='puPickUpAvailFrom_Date',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='PickUp Available From'),
        ),
    ]
