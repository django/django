from django.db import migrations, models

from ..fields import FieldForTesting


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PSQLAutoIDModel",
            fields=[
                (
                    "id",
                    FieldForTesting(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            bases=(models.Model,),
        ),
    ]
