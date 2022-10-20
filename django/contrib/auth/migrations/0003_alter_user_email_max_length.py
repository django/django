from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0002_alter_permission_name_max_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                max_length=254, verbose_name="email address", blank=True
            ),
        ),
    ]
