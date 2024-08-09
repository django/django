from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bar", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="simplebar",
            table="foo_simplebar",
        ),
    ]
