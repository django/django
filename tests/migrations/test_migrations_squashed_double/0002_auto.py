from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="a",
            name="foo",
            field=models.BooleanField(default=True),
        ),
    ]
