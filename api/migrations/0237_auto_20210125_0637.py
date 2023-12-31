# Generated by Django 2.1.2 on 2021-01-25 06:37

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0236_auto_20210125_0313"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookingcostoption",
            name="z_createdAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="bookingcostoption",
            name="z_createdBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="bookingcostoption",
            name="z_modifiedAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="bookingcostoption",
            name="z_modifiedBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="costoption",
            name="z_createdAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="costoption",
            name="z_createdBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="costoption",
            name="z_modifiedAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="costoption",
            name="z_modifiedBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="costoptionmap",
            name="z_createdAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="costoptionmap",
            name="z_createdBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="costoptionmap",
            name="z_modifiedAt",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="costoptionmap",
            name="z_modifiedBy",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
