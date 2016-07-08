# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.SeparateDatabaseAndState([], [
            migrations.CreateModel(
                name='B',
                fields=[
                    ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ],
            ),
        ])
    ]
