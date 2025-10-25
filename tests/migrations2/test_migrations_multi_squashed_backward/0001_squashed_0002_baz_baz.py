from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("migrations2", "0001_initial"),
        ("migrations2", "0002_baz_baz"),
    ]

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Baz",
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
                ("foo", models.CharField(max_length=100)),
                ("baz", models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
    ]
