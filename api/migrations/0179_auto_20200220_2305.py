# Generated by Django 2.1.2 on 2020-02-20 23:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0178_auto_20200219_0616"),
    ]

    operations = [
        migrations.AddField(
            model_name="utl_states",
            name="sender_code",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="Sender Code"
            ),
        ),
    ]
