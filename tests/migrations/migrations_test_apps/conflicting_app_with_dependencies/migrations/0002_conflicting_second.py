from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conflicting_app_with_dependencies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            "Something",
            [
                ("id", models.BigAutoField(primary_key=True)),
            ],
        )
    ]
