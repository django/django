from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0008_alter_user_username_max_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="last name"
            ),
        ),
    ]
