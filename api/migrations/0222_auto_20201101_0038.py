# Generated by Django 2.1.2 on 2020-11-01 00:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0221_merge_20201101_0038"),
    ]

    operations = [
        migrations.AddField(
            model_name="bok_2_lines",
            name="picked_up_timestamp",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="bok_2_lines",
            name="sscc",
            field=models.CharField(blank=True, default=None, max_length=32, null=True),
        ),
    ]
