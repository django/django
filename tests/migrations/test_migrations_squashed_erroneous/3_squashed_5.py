from django.db import migrations


class Migration(migrations.Migration):

    replaces = [
        ("migrations", "3_auto"),
        ("migrations", "4_auto"),
        ("migrations", "5_auto"),
    ]

    dependencies = [("migrations", "2_auto")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop)
    ]
