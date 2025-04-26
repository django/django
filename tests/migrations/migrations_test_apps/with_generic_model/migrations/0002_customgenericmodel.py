from django.db import migrations, models

from ..models import Child


class Migration(migrations.Migration):

    dependencies = [
        ("with_generic_model", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomGenericModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            bases=(
                Child,
                models.Model,
            ),
        ),
    ]
