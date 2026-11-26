from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            [],
            [
                migrations.CreateModel(
                    name="Hub",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
                migrations.CreateModel(
                    name="A",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "hub",
                            models.ForeignKey("delayed_reload_b.Hub", models.CASCADE),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    name="B",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "a",
                            models.ForeignKey("delayed_reload_b.A", models.CASCADE),
                        ),
                    ],
                ),
                migrations.CreateModel(
                    name="C",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                        (
                            "hub",
                            models.ForeignKey("delayed_reload_b.Hub", models.CASCADE),
                        ),
                    ],
                ),
            ],
        ),
    ]
