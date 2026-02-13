from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.AutoField(primary_key=True)),
                (
                    "manager",
                    models.ForeignKey(
                        "self",
                        on_delete=models.SET_NULL,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
