# Generated by Django 2.1.2 on 2021-11-15 04:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0290_merge_20211115_0405"),
    ]

    operations = [
        migrations.AlterField(
            model_name="api_booking_confirmation_lines",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
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
            model_name="bok_1_headers",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_2_lines",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_2_lines",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_3_lines_data",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bok_3_lines_data",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Modified Timestamp"
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
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bookings",
            name="z_CreatedTimestamp",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="bookings",
            name="z_ModifiedTimestamp",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name="bookingsets",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="bookingsets",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
            model_name="client_fp",
            name="z_createdTimeStamp",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="client_process_mgr",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="client_products",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="client_products",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="client_ras",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="client_ras",
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
            model_name="dme_email_templates",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_error",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_error",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="z_createdTimeStamp",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="dme_label_settings",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_label_settings",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
            model_name="dme_options",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
            model_name="dme_reports",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_service_codes",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="dme_service_codes",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
            model_name="fc_log",
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
            model_name="fp_label_scans",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_service_etds",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_service_etds",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="fp_store_booking_log",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="z_createdTimeStamp",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created Timestamp"
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="z_modifiedTimeStamp",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Modified Timestamp"
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
