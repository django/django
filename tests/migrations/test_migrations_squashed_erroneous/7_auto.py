from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("migrations", "6_auto")]

    operations = [migrations.RunPython(migrations.RunPython.noop)]
