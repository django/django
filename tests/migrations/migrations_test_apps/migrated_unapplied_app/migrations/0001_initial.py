# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    operations = [

        migrations.CreateModel(
            "OtherAuthor",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(null=True)),
                ("age", models.IntegerField(default=0)),
                ("silly_field", models.BooleanField(default=False)),
            ],
        ),

    ]
