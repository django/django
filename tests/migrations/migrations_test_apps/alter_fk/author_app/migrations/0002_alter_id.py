# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('author_app', '0001_initial'),
        ('book_app', '0001_initial'),  # Forces the book table to alter the FK
    ]

    operations = [
        migrations.AlterField(
            model_name='author',
            name='id',
            field=models.CharField(max_length=10, primary_key=True),
        ),
    ]
