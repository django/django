from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0002_rename_name_foo_rename"),
    ]

    operations = [
        migrations.AddField(
            model_name="foo",
            name="another_field",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
