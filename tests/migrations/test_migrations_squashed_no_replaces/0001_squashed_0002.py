from django.db import migrations, models


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                (
                    "author",
                    models.ForeignKey("migrations.Author", models.SET_NULL, null=True),
                ),
            ],
        ),
    ]
