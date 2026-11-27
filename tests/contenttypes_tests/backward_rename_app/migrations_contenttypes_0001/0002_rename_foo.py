from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app_backward_rename", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel("Foo", "RenamedFoo"),
    ]
