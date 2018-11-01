from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0004_alter_user_username_opts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
    ]
