from django.db import migrations


def get_for_models(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.get_for_models(
        apps.all_models['contenttypes_tests']['bar'],
        apps.all_models['contenttypes_tests']['baz'],
        apps.all_models['contenttypes_tests']['renamedfoo']
    )


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes_tests', '0002_rename_foo'),
    ]

    operations = [
        migrations.RunPython(get_for_models, migrations.RunPython.noop)
    ]
