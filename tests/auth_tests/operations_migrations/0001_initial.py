from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.CreateModel(
            "OldModel",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
        migrations.RenameModel("OldModel", "NewModel"),
    ]
