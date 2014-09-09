# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('session_key', models.CharField(max_length=40, serialize=False, verbose_name='session key', primary_key=True)),
                ('session_data', models.TextField(verbose_name='session data')),
                ('expire_date', models.DateTimeField(verbose_name='expire date', db_index=True)),
            ],
            options={
                'db_table': 'django_session',
                'verbose_name': 'session',
                'verbose_name_plural': 'sessions',
            },
            bases=(models.Model,),
        ),
    ]
