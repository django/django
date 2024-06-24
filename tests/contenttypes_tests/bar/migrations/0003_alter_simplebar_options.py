from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bar", "0002_alter_simplebar_table"),
        ("foo", "0002_simplebar"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="simplebar",
            options={"managed": False},
        ),
    ]
