# Generated by Django 2.1.2 on 2019-05-25 22:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0095_auto_20190521_2137'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookings',
            name='tally_delivered',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
