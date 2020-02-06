# Generated by Django 2.1.2 on 2020-02-06 06:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0166_auto_20200206_0039"),
    ]

    operations = [
        migrations.AddField(
            model_name="fp_pricing_rules",
            name="timing",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.FP_timings",
            ),
        ),
        migrations.AddField(
            model_name="fp_vehicles",
            name="max_mass",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AlterField(
            model_name="fp_pricing_rules",
            name="cost",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.FP_costs",
            ),
        ),
    ]
