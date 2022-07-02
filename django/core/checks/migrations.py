from django.core.checks import Tags, register


@register(Tags.migrations)
def check_migration_operations(**kwargs):
    from django.db.migrations.loader import MigrationLoader

    errors = []
    loader = MigrationLoader(None, ignore_no_migrations=True)
    for migration in loader.disk_migrations.values():
        errors.extend(migration.check())
    return errors
