# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def raise_error(apps, schema_editor):
    # Test atomic operation in non-atomic migration is wrapped in transaction
    Editor = apps.get_model('migrations', 'Editor')
    Editor.objects.create(name='Test Editor')
    raise RuntimeError('Abort migration')


class Migration(migrations.Migration):
    atomic = False

    operations = [
        migrations.CreateModel(
            "Editor",
            [
                ("name", models.CharField(primary_key=True, max_length=255)),
            ],
        ),
        migrations.RunPython(raise_error, atomic=True),
    ]
