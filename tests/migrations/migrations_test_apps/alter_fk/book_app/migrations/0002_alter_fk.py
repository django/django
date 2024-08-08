from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("author_app", "0001_initial"),
        ("book_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="Book",
            name="author2",
            field=models.ForeignKey("author_app.Author", models.CASCADE),
        ),
    ]
