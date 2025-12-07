from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="C1",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
            ],
        ),
    ]
