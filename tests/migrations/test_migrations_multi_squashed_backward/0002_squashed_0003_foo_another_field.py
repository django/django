from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("migrations", "0002_rename_name_foo_rename"),
        ("migrations", "0003_foo_another_field"),
    ]

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="foo",
            old_name="name",
            new_name="rename",
        ),
        migrations.AddField(
            model_name="foo",
            name="another_field",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
