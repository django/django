# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contenttype',
            options={'verbose_name': 'content type', 'verbose_name_plural': 'content types'},
        ),
        migrations.RemoveField(
            model_name='contenttype',
            name='name',
        ),
    ]
