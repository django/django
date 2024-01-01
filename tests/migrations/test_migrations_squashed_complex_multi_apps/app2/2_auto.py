from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("app2", "1_auto")]

    operations = [migrations.RunPython(migrations.RunPython.noop)]
