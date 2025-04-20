from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth_tests", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="OldModel",
            new_name="NewModel",
        ),
    ]
