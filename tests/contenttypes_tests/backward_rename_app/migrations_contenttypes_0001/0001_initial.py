from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            "Foo",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
