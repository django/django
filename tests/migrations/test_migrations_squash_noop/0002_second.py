# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def dummy_python_op(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(dummy_python_op, migrations.RunPython.noop, elidable=False),
    ]
