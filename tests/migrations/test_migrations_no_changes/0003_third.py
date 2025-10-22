from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("migrations", "0002_second"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModelWithCustomBase",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="UnmigratedModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.DeleteModel(
            name="Author",
        ),
        migrations.DeleteModel(
            name="Book",
        ),
    ]
