# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-07-27 11:40
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('project_data', '0007_auto_20160726_0525'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplainStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(max_length=100, null=True)),
                ('change_time', models.CharField(max_length=100, null=True)),
                ('bkash_agent', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stat_agent', to=settings.AUTH_USER_MODEL)),
                ('complain', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stat_complain', to='project_data.Complain')),
            ],
        ),
    ]