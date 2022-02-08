from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0002_second"),
    ]

    operations = [
        migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RunSQL(
            ["SELECT * FROM migrations_author"], ["SELECT * FROM migrations_book"]
        ),
    ]
