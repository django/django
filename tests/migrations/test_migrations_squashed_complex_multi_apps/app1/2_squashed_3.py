from django.db import migrations


class Migration(migrations.Migration):
    replaces = [
        ("app1", "2_auto"),
        ("app1", "3_auto"),
    ]

    dependencies = [("app1", "1_auto"), ("app2", "2_auto")]

    operations = [migrations.RunPython(migrations.RunPython.noop)]
