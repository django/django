from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app_a", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OtherModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("title", models.CharField(max_length=50)),
                ("my_model", models.ForeignKey("app_a.MyModel", models.CASCADE)),
            ],
        ),
    ]
