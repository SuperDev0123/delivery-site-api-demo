# Generated by Django 2.1.2 on 2019-05-20 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0090_auto_20190520_1949'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userpermissions',
            old_name='user_id',
            new_name='user',
        ),
    ]
