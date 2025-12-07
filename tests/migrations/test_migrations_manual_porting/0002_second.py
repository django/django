from django.db import migrations


def forwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
