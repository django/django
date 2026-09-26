from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth_tests", "0002_rename_oldmodel_to_newmodel"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="NewModel",
            new_name="AnotherModel",
        ),
    ]
