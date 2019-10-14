from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.RunSQL(migrations.RunSQL.noop, migrations.RunSQL.noop),
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
