from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bar", "0003_alter_simplebar_options"),
        ("foo", "0003_alter_simplebar_options_alter_foowithfk_bar"),
    ]

    operations = [
        migrations.DeleteModel(
            name="simplebar",
        ),
    ]
