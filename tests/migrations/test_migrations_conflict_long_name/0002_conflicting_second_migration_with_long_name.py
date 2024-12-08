from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0001_initial")]

    operations = [
        migrations.CreateModel(
            "SomethingElse",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
