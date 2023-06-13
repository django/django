from django.contrib.auth import validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0003_alter_user_email_max_length"),
    ]

    # No database changes; modifies validators and error_messages (#13147).
    operations = [
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                error_messages={"unique": "A user with that username already exists."},
                max_length=30,
                validators=[validators.UnicodeUsernameValidator()],
                help_text=(
                    "Required. 30 characters or fewer. Letters, digits and @/./+/-/_ "
                    "only."
                ),
                unique=True,
                verbose_name="username",
            ),
        ),
    ]
