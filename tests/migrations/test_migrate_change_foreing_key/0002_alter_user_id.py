import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("migrations", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="id",
            field=models.CharField(default=uuid.uuid4, max_length=32, primary_key=True),
        ),
    ]
