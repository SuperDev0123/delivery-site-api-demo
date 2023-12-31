# Generated by Django 2.1.2 on 2022-02-24 02:17

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0304_auto_20220208_0911"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="bookingcostoption",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="bookingcostoption",
            name="booking",
        ),
        migrations.RemoveField(
            model_name="bookingcostoption",
            name="cost_option",
        ),
        migrations.RemoveField(
            model_name="costoptionmap",
            name="dme_cost_option",
        ),
        migrations.RemoveField(
            model_name="costoptionmap",
            name="fp",
        ),
        migrations.AddField(
            model_name="surcharge",
            name="applied_at",
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name="surcharge",
            name="booking",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.Bookings",
            ),
        ),
        migrations.AddField(
            model_name="surcharge",
            name="connote_or_reference",
            field=models.CharField(default=None, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="surcharge",
            name="is_manually_entered",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="surcharge",
            name="visible",
            field=models.BooleanField(default=False),
        ),
        migrations.DeleteModel(
            name="BookingCostOption",
        ),
        migrations.DeleteModel(
            name="CostOption",
        ),
        migrations.DeleteModel(
            name="CostOptionMap",
        ),
    ]
