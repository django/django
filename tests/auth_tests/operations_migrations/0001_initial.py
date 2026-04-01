from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    operations = [
        migrations.CreateModel(
            name="OldModel",
            fields=[
                ("id", models.AutoField(primary_key=True)),
            ],
        ),
    ]
