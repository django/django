# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lookuperror_a', '0002_a2'),
        ('lookuperror_b', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='B2',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('a1', models.ForeignKey(to='lookuperror_a.A1')),
            ],
        ),
    ]
