# Generated by Django 2.1.2 on 2019-03-18 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0048_auto_20190318_1905'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dme_comm_notes',
            name='note_date_created',
            field=models.DateField(verbose_name='Created Timestamp'),
        ),
        migrations.AlterField(
            model_name='dme_comm_notes',
            name='note_date_updated',
            field=models.DateField(verbose_name='Created Timestamp'),
        ),
        # migrations.AlterField(
        #     model_name='utl_states',
        #     name='fk_country_id',
        #     field=models.CharField(blank=True, default='', max_length=32, null=True),
        # ),
    ]
