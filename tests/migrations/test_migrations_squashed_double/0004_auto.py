from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("migrations", "0002_auto")]
    operations = [
        migrations.AlterField(
            model_name="a",
            name="foo",
            field=models.BooleanField(default=False),
        ),
    ]
