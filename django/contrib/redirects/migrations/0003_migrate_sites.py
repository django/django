from django.db import migrations


def migrate_site_domains(apps, schema_editor):
    try:
        Site = apps.get_model('sites', 'Site')
    except LookupError:
        return

    Redirect = apps.get_model('redirects', 'Redirect')

    db_alias = schema_editor.connection.alias
    for r in Redirect.objects.using(db_alias).all():
        try:
            site = Site.objects.get(id=r.site_id)
        except Site.DoesNotExist:
            continue

        r.domain = site.domain
        r.save(update_fields=('domain',))


class Migration(migrations.Migration):

    dependencies = [
        ('redirects', '0002_add_domain'),
    ]

    operations = [
        migrations.RunPython(migrate_site_domains, migrations.RunPython.noop),
    ]
