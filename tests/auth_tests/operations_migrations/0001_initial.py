# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OldModel",
            fields=[
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
