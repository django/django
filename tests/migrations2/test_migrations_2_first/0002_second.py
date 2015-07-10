# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("migrations2", "0001_initial")]

    operations = [

        migrations.CreateModel(
            "Bookstore",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(null=True)),
            ],
        ),

    ]
