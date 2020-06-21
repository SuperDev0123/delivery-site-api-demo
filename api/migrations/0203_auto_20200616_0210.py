# Generated by Django 2.1.2 on 2020-06-16 02:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0202_auto_20200611_1131"),
    ]

    operations = [
        migrations.RemoveField(model_name="bookingsets", name="z_createdTimestamp",),
        migrations.RemoveField(model_name="bookingsets", name="z_modifiedTimestamp",),
        migrations.RemoveField(
            model_name="dme_email_templates", name="z_downloadedByAccount",
        ),
        migrations.RemoveField(
            model_name="dme_email_templates", name="z_downloadedTimeStamp",
        ),
        migrations.RemoveField(
            model_name="dme_label_settings", name="z_downloadedByAccount",
        ),
        migrations.RemoveField(
            model_name="dme_label_settings", name="z_downloadedTimeStamp",
        ),
        migrations.RemoveField(model_name="dme_options", name="z_downloadedTimeStamp",),
        migrations.RemoveField(model_name="dme_reports", name="z_downloadedByAccount",),
        migrations.RemoveField(model_name="dme_reports", name="z_downloadedTimeStamp",),
        migrations.RemoveField(
            model_name="dme_service_codes", name="z_createdTimestamp",
        ),
        migrations.RemoveField(
            model_name="dme_service_codes", name="z_modifiedTimestamp",
        ),
        migrations.RemoveField(
            model_name="fp_service_etds", name="z_createdTimestamp",
        ),
        migrations.RemoveField(
            model_name="fp_service_etds", name="z_modifiedTimestamp",
        ),
        migrations.AddField(
            model_name="bok_1_headers",
            name="x_booking_Created_With",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name="Booking Created With",
            ),
        ),
        migrations.AddField(
            model_name="bok_1_headers",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AddField(
            model_name="bok_1_headers",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AddField(
            model_name="bok_1_headers",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="bok_2_lines",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AddField(
            model_name="bok_2_lines",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AddField(
            model_name="bok_2_lines",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="bookingsets",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="bookingsets",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_email_templates",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AddField(
            model_name="dme_email_templates",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_label_settings",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AddField(
            model_name="dme_label_settings",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_options",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_reports",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AddField(
            model_name="dme_reports",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_service_codes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="dme_service_codes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="fp_label_scans",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="fp_service_etds",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AddField(
            model_name="fp_service_etds",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_confirmation_lines",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_confirmation_lines",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_confirmation_lines",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_confirmation_lines",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_quotes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_quotes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_quotes_confirmation",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="api_booking_quotes_confirmation",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_1_headers",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_2_lines",
            name="pk_booking_lines_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="bok_2_lines",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_3_lines_data",
            name="fk_booking_lines_id",
            field=models.CharField(blank=True, default=None, max_length=64),
        ),
        migrations.AlterField(
            model_name="booking_lines",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines_data",
            name="fk_booking_lines_id",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=64,
                null=True,
                verbose_name="FK Booking Lines Id",
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines_data",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines_data",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines_data",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="booking_lines_data",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
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
            model_name="bookings",
            name="x_booking_Created_With",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name="Booking Created With",
            ),
        ),
        migrations.AlterField(
            model_name="bookingsets",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="bookingsets",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="client_employees",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="client_employees",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_comm_and_task",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_comm_and_task",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_comm_notes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_comm_notes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_email_templates",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_label_settings",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_manifest_log",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_manifest_log",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_options",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_package_types",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_package_types",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_reports",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_service_codes",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="dme_service_codes",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="dme_status_history",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_status_history",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_utl_client_customer_group",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_utl_client_customer_group",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_utl_fp_statuses",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_utl_fp_statuses",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="emaillogs",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_freight_providers",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_freight_providers",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_label_scans",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_service_etds",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="fp_service_etds",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="ruletypes",
            name="z_createdByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Created by account"
            ),
        ),
        migrations.AlterField(
            model_name="ruletypes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="ruletypes",
            name="z_modifiedByAccount",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Modified by account"
            ),
        ),
        migrations.AlterField(
            model_name="ruletypes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="tokens",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_country_codes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_country_codes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status_actions",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status_actions",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status_details",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_dme_status_details",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_fp_delivery_times",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_fp_delivery_times",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_sql_queries",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_sql_queries",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_states",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_states",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_suburbs",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="utl_suburbs",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
    ]
