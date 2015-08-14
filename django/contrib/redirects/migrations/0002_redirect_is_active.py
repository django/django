# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('redirects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='redirect',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Active?'),
        ),
    ]
