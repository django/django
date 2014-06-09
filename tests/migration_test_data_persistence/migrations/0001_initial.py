# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_book(apps, schema_editor):
    apps.get_model("migration_test_data_persistence", "Book").objects.using(
        schema_editor.connection.alias,
    ).create(
        title="I Love Django",
    )


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('title', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(
            add_book,
        ),
    ]
