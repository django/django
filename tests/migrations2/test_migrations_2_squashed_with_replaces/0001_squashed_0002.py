from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [
        ("migrations2", "0001_initial"),
        ("migrations2", "0002_second"),
    ]

    operations = [
        migrations.CreateModel(
            "OtherAuthor",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            "OtherBook",
            [
                ("id", models.AutoField(primary_key=True)),
                (
                    "author",
                    models.ForeignKey(
                        "migrations2.OtherAuthor", models.SET_NULL, null=True
                    ),
                ),
            ],
        ),
    ]
