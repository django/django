from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("migrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="projects",
            field=models.ManyToManyField(to="Project"),
        ),
    ]
