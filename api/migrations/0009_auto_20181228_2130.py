# Generated by Django 2.1.2 on 2018-12-28 21:30

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_auto_20181226_1846'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bok_2_lines',
            old_name='pk_auto_id',
            new_name='pk_lines_id',
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='date_processed',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, verbose_name='Date Pocessed'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='e_item_type',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Item Type'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='e_item_type_new',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Item Type New'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='e_pallet_type',
            field=models.CharField(blank=True, max_length=24, null=True, verbose_name='Pallet Type'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='fk_header_id',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Header id'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_001_type_of_packaging',
            field=models.CharField(blank=True, max_length=24, null=True, verbose_name='Type Of Packaging'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_005_dim_length',
            field=models.IntegerField(blank=True, null=True, verbose_name='DIM Length'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_006_dim_width',
            field=models.IntegerField(blank=True, null=True, verbose_name='DIM Width'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_007_dim_height',
            field=models.IntegerField(blank=True, null=True, verbose_name='DIM Height'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_008_weight_UOM',
            field=models.IntegerField(blank=True, null=True, verbose_name='DIM Weight'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_009_weight_per_each_original',
            field=models.IntegerField(blank=True, null=True, verbose_name='Weight Per Each Original'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='l_500_b_client_cust_job_code',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Client Cust Job Code'),
        ),
        migrations.AddField(
            model_name='bok_2_lines',
            name='z_createdTimeStamp',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, verbose_name='Created Timestamp'),
        ),
        migrations.AlterField(
            model_name='bok_2_lines',
            name='l_501_client_UOM',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Client UOM'),
        ),
    ]
