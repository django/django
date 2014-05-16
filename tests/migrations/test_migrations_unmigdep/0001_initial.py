# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "__first__"),
    ]

    operations = [

        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("user", models.ForeignKey("auth.User", null=True)),
            ],
        )

    ]
