# Generated by Django 2.1.2 on 2019-05-20 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0087_auto_20190520_1832'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userpermissions',
            old_name='comms_drop_down',
            new_name='can_create_comm',
        ),
    ]
