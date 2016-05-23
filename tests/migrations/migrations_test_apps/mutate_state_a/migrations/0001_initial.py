# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mutate_state_b', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState([], [
            migrations.CreateModel(
                name='A',
                fields=[
                    ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ],
            ),
        ])
    ]
