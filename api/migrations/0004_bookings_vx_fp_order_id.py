# Generated by Django 2.1.2 on 2019-02-12 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_dme_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookings',
            name='vx_fp_order_id',
            field=models.CharField(blank=True, default='', max_length=64, null=True, verbose_name='Order ID'),
        ),
    ]
