# Generated by Django 2.1.2 on 2019-05-20 19:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0088_auto_20190520_1901'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userpermissions',
            name='user',
        ),
        migrations.AddField(
            model_name='userpermissions',
            name='user_id',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='userpermissions',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
