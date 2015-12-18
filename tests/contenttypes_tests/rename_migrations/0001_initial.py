# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_foo_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.create(app_label="contenttypes_tests", model="foo")


def delete_foo_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    count, _details = ContentType.objects.filter(app_label="contenttypes_tests", model="foo").delete()
    assert count == 1


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            "Foo",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            "Bar",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RunPython(create_foo_content_type, delete_foo_content_type),
        migrations.RenameModel("Foo", "RenamedFoo"),
        migrations.RenameModel("Bar", "Renamedbar"),
    ]
