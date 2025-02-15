import thibaud.contrib.postgres.fields
from thibaud.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("postgres_tests", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="integerarraydefaultmodel",
            name="field_2",
            field=thibaud.contrib.postgres.fields.ArrayField(
                models.IntegerField(), default=[], size=None
            ),
            preserve_default=False,
        ),
    ]
