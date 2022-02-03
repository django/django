from django.db import migrations


class Migration(migrations.Migration):

    replaces = [
        ("app2", "1_auto"),
        ("app2", "2_auto"),
    ]

    dependencies = [("app1", "1_auto")]

    operations = [migrations.RunPython(migrations.RunPython.noop)]
