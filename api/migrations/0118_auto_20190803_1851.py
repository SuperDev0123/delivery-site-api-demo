# Generated by Django 2.1.2 on 2019-08-03 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api", "0117_auto_20190803_1848")]

    operations = [
        migrations.RenameField(
            model_name="fp_carriers", old_name="end_value", new_name="connote_end_value"
        ),
        migrations.RenameField(
            model_name="fp_carriers",
            old_name="start_value",
            new_name="connote_start_value",
        ),
        migrations.AddField(
            model_name="fp_carriers",
            name="label_end_value",
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="fp_carriers",
            name="label_start_value",
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]
