from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lookuperror_b", "0002_b2"),
    ]

    operations = [
        migrations.CreateModel(
            name="B3",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        primary_key=True,
                        auto_created=True,
                    ),
                ),
            ],
        ),
    ]
