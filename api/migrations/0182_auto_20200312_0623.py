# Generated by Django 2.1.2 on 2020-03-12 06:23

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0181_auto_20200310_0739"),
    ]

    operations = [
        migrations.CreateModel(
            name="Client_Auto_Augment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tic_de_Email",
                    models.CharField(
                        blank=True,
                        default="itassets@ticgroup.com.au",
                        max_length=64,
                        null=True,
                        verbose_name="TIC DE Email",
                    ),
                ),
                (
                    "tic_de_Email_Group_Emails",
                    models.CharField(
                        blank=True,
                        default="rloqa@ticgroup.com.au",
                        max_length=30,
                        null=True,
                        verbose_name="TIC DE Email Group Emails",
                    ),
                ),
                (
                    "tic_de_To_Address_Street_1",
                    models.CharField(
                        blank=True,
                        default="Door 13, Building 2",
                        max_length=40,
                        null=True,
                        verbose_name="TIC DE Address Street 1",
                    ),
                ),
                (
                    "tic_de_To_Address_Street_2",
                    models.CharField(
                        blank=True,
                        default="207 Sunshine Road",
                        max_length=40,
                        null=True,
                        verbose_name="TIC DE Address Street 2",
                    ),
                ),
                (
                    "sales_club_de_Email",
                    models.CharField(
                        blank=True,
                        default="alan.bortz@salesclub.com.au",
                        max_length=64,
                        null=True,
                        verbose_name="Sales Club DE Email",
                    ),
                ),
                (
                    "sales_club_de_Email_Group_Emails",
                    models.TextField(
                        blank=True,
                        default="stock@salesclub.com.au, suraj@salesclub.com.au, Patrick@factoryseconds.biz, david@factoryseconds.biz",
                        max_length=512,
                        null=True,
                        verbose_name="Sales Club DE Email Group Emails",
                    ),
                ),
            ],
            options={"db_table": "client_auto_augment",},
        ),
        migrations.CreateModel(
            name="Client_Process_Mgr",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fk_booking_id",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=64,
                        null=True,
                        verbose_name="Booking ID",
                    ),
                ),
                (
                    "process_name",
                    models.CharField(max_length=40, verbose_name="Process Name"),
                ),
                (
                    "z_createdTimeStamp",
                    models.DateTimeField(
                        blank=True,
                        default=datetime.datetime.now,
                        verbose_name="Created Timestamp",
                    ),
                ),
                (
                    "origin_puCompany",
                    models.CharField(max_length=128, verbose_name="Origin PU Company"),
                ),
                (
                    "origin_pu_Address_Street_1",
                    models.CharField(
                        max_length=40, verbose_name="Origin PU Address Street1"
                    ),
                ),
                (
                    "origin_pu_Address_Street_2",
                    models.CharField(
                        max_length=40, verbose_name="Origin PU Address Street2"
                    ),
                ),
                (
                    "origin_pu_pickup_instructions_address",
                    models.TextField(
                        blank=True,
                        default="",
                        max_length=512,
                        null=True,
                        verbose_name="Origin PU instrunctions address",
                    ),
                ),
                (
                    "origin_deToCompanyName",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=128,
                        null=True,
                        verbose_name="Origin DE Company Name",
                    ),
                ),
                (
                    "origin_de_Email",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=64,
                        null=True,
                        verbose_name="Origin DE Email",
                    ),
                ),
                (
                    "origin_de_Email_Group_Emails",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=30,
                        null=True,
                        verbose_name="Origin DE Email Group Emails",
                    ),
                ),
                (
                    "origin_de_To_Address_Street_1",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=40,
                        null=True,
                        verbose_name="Origin DE Address Street 1",
                    ),
                ),
                (
                    "origin_de_To_Address_Street_2",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=40,
                        null=True,
                        verbose_name="Origin DE Address Street 2",
                    ),
                ),
                (
                    "origin_pu_PickUp_By_Date",
                    models.DateField(
                        blank=True, null=True, verbose_name="Origin PU By Date DME"
                    ),
                ),
                (
                    "origin_pu_PickUp_Avail_Time_Hours",
                    models.IntegerField(
                        blank=True,
                        default=0,
                        null=True,
                        verbose_name="Origin PU Available Time Hours",
                    ),
                ),
            ],
            options={"db_table": "client_process_mgr",},
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="file_extension",
            field=models.CharField(max_length=8, verbose_name="File Extension"),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="file_name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="file_type",
            field=models.CharField(max_length=16, verbose_name="File Type"),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="note",
            field=models.TextField(max_length=512, verbose_name="Note"),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="z_createdByAccount",
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name="dme_files",
            name="z_createdTimeStamp",
            field=models.DateTimeField(blank=True, default=datetime.datetime.now),
        ),
    ]
