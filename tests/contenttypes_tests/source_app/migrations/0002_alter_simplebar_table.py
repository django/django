from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("source_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="simplebar",
            table="target_app_simplebar",
        ),
    ]
