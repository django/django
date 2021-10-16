from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('redirects', '0002_alter_redirect_new_path_help_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='redirect',
            name='redirect_type',
            field=models.IntegerField(
                choices=[(301, 'Moved Permanently'), (302, 'Found'), (410, 'Gone')],
                verbose_name='redirect type',
            ),
        ),
    ]
