from django.db import migrations, models


class Migration(migrations.Migration):
    operations = [
        migrations.CreateModel(
            "Foo",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
