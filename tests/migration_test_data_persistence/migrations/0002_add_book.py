from django.db import migrations, models


def add_book(apps, schema_editor):
    apps.get_model("migration_test_data_persistence", "Book").objects.using(
        schema_editor.connection.alias,
    ).create(
        title="I Love Django",
    )


class Migration(migrations.Migration):
    dependencies = [("migration_test_data_persistence", "0001_initial")]

    operations = [
        migrations.RunPython(
            add_book,
        ),
        migrations.CreateModel(
            name="Unmanaged",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100)),
            ],
            options={
                "managed": False,
            },
        ),
        migrations.AlterField(
            model_name="book",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
