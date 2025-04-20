# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    operations = [
        migrations.CreateModel(
            "OldModel",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RenameModel("OldModel", "NewModel"),
    ]
