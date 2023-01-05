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
                (
                    "author",
                    models.ForeignKey("migrations.Author", models.SET_NULL, null=True),
                ),
            ],
        )
    ]
