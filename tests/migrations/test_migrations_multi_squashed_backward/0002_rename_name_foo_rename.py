from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="foo",
            old_name="name",
            new_name="rename",
        ),
    ]
