from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField("Author", "rating", models.IntegerField(default=0)),
        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
                ("author", models.ForeignKey("migrations.Author", models.SET_NULL, null=True)),
            ],
        ),
    ]
