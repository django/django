from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("source_app", "0002_alter_simplebar_table"),
        ("target_app", "0002_simplebar"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="simplebar",
            options={"managed": False},
        ),
    ]
