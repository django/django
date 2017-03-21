from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("app1", "2_auto"), ("app2", "2_auto")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop)
    ]
