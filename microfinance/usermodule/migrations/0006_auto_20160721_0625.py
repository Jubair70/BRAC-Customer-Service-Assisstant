# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-07-21 06:25
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usermodule', '0005_usersecuritycode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersecuritycode',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_user_fk', to=settings.AUTH_USER_MODEL),
        ),
    ]
