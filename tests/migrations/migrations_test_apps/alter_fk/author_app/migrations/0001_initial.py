from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("name", models.CharField(max_length=50)),
            ],
        ),
    ]
