# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-18 19:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0005_auto_20151217_1928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='datasets.Dataset'),
        ),
    ]
