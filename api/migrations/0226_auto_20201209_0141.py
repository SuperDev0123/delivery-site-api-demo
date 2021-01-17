# Generated by Django 2.1.2 on 2020-12-09 01:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0225_auto_20201207_0036"),
    ]

    operations = [
        migrations.CreateModel(
            name="DME_Augment_Address",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("origin_word", models.CharField(blank=True, max_length=32, null=True)),
                (
                    "augmented_word",
                    models.CharField(blank=True, max_length=32, null=True),
                ),
            ],
            options={
                "db_table": "dme_augment_address",
            },
        ),
        migrations.RenameField(
            model_name="dme_options",
            old_name="z_downloadedByAccount",
            new_name="z_modifiedByAccount",
        ),
        migrations.RemoveField(
            model_name="bok_2_lines",
            name="is_deleted",
        ),
        migrations.RemoveField(
            model_name="bok_2_lines",
            name="picked_up_timestamp",
        ),
        migrations.RemoveField(
            model_name="bok_2_lines",
            name="sscc",
        ),
        migrations.AddField(
            model_name="booking_lines",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="booking_lines",
            name="sscc",
            field=models.CharField(blank=True, default=None, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name="api_booking_quotes",
            name="service_code",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="Service Code"
            ),
        ),
        migrations.AlterField(
            model_name="bok_1_headers",
            name="quote",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.API_booking_quotes",
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines",
            name="pk_booking_lines_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="bookings",
            name="api_booking_quote",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.API_booking_quotes",
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
    ]
