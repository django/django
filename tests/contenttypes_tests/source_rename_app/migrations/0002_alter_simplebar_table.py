from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("source_rename_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="simplebar",
            table="target_rename_app_renamedsimplebar",
        ),
    ]
