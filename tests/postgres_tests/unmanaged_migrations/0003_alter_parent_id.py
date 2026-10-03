from django.db import migrations, models

# Such a migration is created by makemigrations when changing e.g.
# DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


class Migration(migrations.Migration):

    dependencies = [
        ("postgres_tests", "0002_child"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parent",
            name="id",
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
