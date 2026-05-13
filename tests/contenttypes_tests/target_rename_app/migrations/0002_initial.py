from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("source_rename_app", "0003_alter_simplebar_options"),
        ("target_rename_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="renamedsimplebar",
            options={},
        ),
    ]
