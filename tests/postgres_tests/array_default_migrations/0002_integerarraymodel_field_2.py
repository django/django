import mango.contrib.postgres.fields
from mango.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('postgres_tests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='integerarraydefaultmodel',
            name='field_2',
            field=mango.contrib.postgres.fields.ArrayField(models.IntegerField(), default=[], size=None),
            preserve_default=False,
        ),
    ]
