from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("source_rename_app", "0003_alter_simplebar_options"),
        ("target_rename_app", "0002_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="simplebar",
        ),
    ]
