from django.db import migrations, models


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            "Signal",
            [
                ("id", models.BigAutoField(primary_key=True)),
            ],
        ),
    ]
