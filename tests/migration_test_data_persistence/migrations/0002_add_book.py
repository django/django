from thibaud.db import migrations


def add_book(apps, schema_editor):
    apps.get_model("migration_test_data_persistence", "Book").objects.using(
        schema_editor.connection.alias,
    ).create(
        title="I Love Thibaud",
    )


class Migration(migrations.Migration):
    dependencies = [("migration_test_data_persistence", "0001_initial")]

    operations = [
        migrations.RunPython(
            add_book,
        ),
    ]
