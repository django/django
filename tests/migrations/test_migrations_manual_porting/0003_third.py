from django.db import migrations


def forwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("migrations", "0002_second"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="somemodel",
            unique_together={("id", "name")},
        ),
        migrations.AlterUniqueTogether(
            name="somemodel",
            unique_together={("name",)},
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
