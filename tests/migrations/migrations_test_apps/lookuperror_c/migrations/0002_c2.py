from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lookuperror_a", "0002_a2"),
        ("lookuperror_c", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="C2",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        verbose_name="ID",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("a1", models.ForeignKey("lookuperror_a.A1", models.CASCADE)),
            ],
        ),
    ]
