from django.db import migrations


class Migration(migrations.Migration):

    replaces = [("migrations", "2_squashed")]
    dependencies = [("migrations", "1_auto")]

    operations = [migrations.RunPython(migrations.RunPython.noop)]
