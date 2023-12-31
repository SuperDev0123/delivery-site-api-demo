# Generated by Django 2.1.2 on 2019-04-05 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0051_auto_20190318_2144'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dme_status_notes',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(blank=True, max_length=64, null=True, verbose_name='status')),
            ],
            options={
                'db_table': 'dme_status_notes',
            },
        ),
        migrations.AlterField(
            model_name='bookings',
            name='pu_Address_Suburb',
            field=models.CharField(blank=True, default='', max_length=50, null=True, verbose_name='PU Address Suburb'),
        ),
        # migrations.AlterField(
        #     model_name='utl_states',
        #     name='fk_country_id',
        #     field=models.CharField(blank=True, default='', max_length=32, null=True),
        # ),
    ]
