# Generated by Django 2.0.8 on 2018-10-02 14:22

from django.db import migrations

import django_eth.models


class Migration(migrations.Migration):

    dependencies = [
        ('relay', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='safemultisigtx',
            name='refund_receiver',
            field=django_eth.models.EthereumAddressField(null=True),
        ),
    ]