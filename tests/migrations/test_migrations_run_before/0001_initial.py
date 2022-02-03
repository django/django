from django.db import migrations, models


class Migration(migrations.Migration):

    operations = [
        migrations.CreateModel(
            "Salamander",
            [
                ("id", models.AutoField(primary_key=True)),
                ("size", models.IntegerField(default=0)),
                ("silly_field", models.BooleanField(default=False)),
            ],
        ),
    ]
