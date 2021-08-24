from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("author_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                ("author", models.ForeignKey("author_app.Author", models.CASCADE)),
            ],
        ),
    ]
