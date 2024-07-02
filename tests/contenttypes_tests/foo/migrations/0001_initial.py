import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("bar", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FooWithFk",
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
                (
                    "bar",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="bar.simplebar"
                    ),
                ),
            ],
        ),
    ]
