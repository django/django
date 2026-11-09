from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app_a", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mymodel",
            name="id",
            field=models.BigAutoField(
                serialize=False, auto_created=True, primary_key=True
            ),
        ),
    ]
