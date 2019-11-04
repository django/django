from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("app1", "3_auto")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop)
    ]
