# Generated by Django 2.1.2 on 2019-05-31 21:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0096_auto_20190525_2228'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dme_comm_notes',
            name='dme_notes',
            field=models.TextField(blank=True, null=True, verbose_name='DME Notes'),
        ),
    ]
