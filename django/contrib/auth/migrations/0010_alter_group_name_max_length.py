from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0009_alter_user_last_name_max_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="group",
            name="name",
            field=models.CharField(max_length=150, unique=True, verbose_name="name"),
        ),
    ]
