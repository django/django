from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("migrations", "0001_initial")]

    operations = [

        migrations.CreateModel(
            "Something",
            [
                ("id", models.BigAutoField(primary_key=True)),
            ],
        )

    ]
