from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("source_app", "0003_alter_simplebar_options"),
        ("target_app", "0003_alter_simplebar_options_alter_foowithfk_bar"),
    ]

    operations = [
        migrations.DeleteModel(
            name="simplebar",
        ),
    ]
