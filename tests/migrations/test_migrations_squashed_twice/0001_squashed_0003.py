from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("migrations", "0001_initial"),
        ("migrations", "0002_second"),
        ("migrations", "0001_squashed_0002"),
        ("migrations", "0003_third"),
    ]

    operations = [

        migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(null=True)),
                ("age", models.IntegerField(default=0)),
                ("rating", models.IntegerField(default=0)),
                ("date_of_birth", models.DateField(null=True)),
            ],
        ),

        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("migrations.Author", models.SET_NULL, null=True)),
            ],
        ),
    ]
