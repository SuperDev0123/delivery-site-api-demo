# Generated by Django 2.1.2 on 2019-05-15 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0084_auto_20190515_1803'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bookings',
            old_name='dme_status_details',
            new_name='dme_status_detail',
        ),
        migrations.RenameField(
            model_name='dme_status_history',
            old_name='dme_status_details',
            new_name='dme_status_detail',
        ),
        migrations.RenameField(
            model_name='utl_dme_status_actions',
            old_name='dme_status_actions',
            new_name='dme_status_action',
        ),
        migrations.RenameField(
            model_name='utl_dme_status_details',
            old_name='dme_status_details',
            new_name='dme_status_detail',
        ),
    ]
