from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RunSQL(
            ["SELECT * FROM migrations_book"], ["SELECT * FROM migrations_salamander"]
        ),
    ]
