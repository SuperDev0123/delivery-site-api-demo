# Generated by Django 2.1.2 on 2022-01-19 06:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0298_auto_20220119_0053"),
    ]

    operations = [
        migrations.AddField(
            model_name="s_bookings",
            name="b_client_id",
            field=models.CharField(blank=True, default=None, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="s_bookings",
            name="b_status_category",
            field=models.CharField(blank=True, default=None, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="s_bookings",
            name="last_cs_note",
            field=models.TextField(default=None, null=True),
        ),
        migrations.AddField(
            model_name="s_bookings",
            name="last_cs_note_timestamp",
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
