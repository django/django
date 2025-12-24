from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [
        ("migrations", "0003_squashed_0001_and_0002"),
        ("migrations", "0004_auto"),
    ]
    operations = [
        migrations.CreateModel(
            name="A",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("foo", models.BooleanField(default=False)),
            ],
        ),
    ]
