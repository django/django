from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured
from django.db import migrations, models


def check_redirects_data(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    Redirect = apps.get_model('redirects', 'Redirect')

    if (Redirect.objects.using(db_alias).exists() and
            not django_apps.is_installed('django.contrib.sites')):
        raise ImproperlyConfigured(
            "You have redirects data in your database, and "
            "'django.contrib.sites' app must be installed in order "
            "to correctly migrate it. Please add it to INSTALLED_APPS."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('redirects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(check_redirects_data, migrations.RunPython.noop),

        migrations.AddField(
            model_name='redirect',
            name='domain',
            field=models.CharField(
                blank=True,
                help_text='If set, redirect requests from this domain only.',
                max_length=255,
                verbose_name='domain'
            ),
        ),

    ]
