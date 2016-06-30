import importlib

from django.db import connections

from . import Tags, Warning, register


@register(Tags.database)
def check_database_backends(*args, **kwargs):
    issues = []
    for conn in connections.all():
        issues.extend(conn.validation.check(**kwargs))
    return issues


@register(Tags.database)
def check_migration_modules(*args, **kwargs):
    from django.conf import settings
    migration_modules = getattr(settings, 'MIGRATION_MODULES', {})
    warnings = []
    for app_label, module in migration_modules.items():
        if module is None:
            continue
        try:
            importlib.import_module(module)
        except ImportError:
            warnings.append(
                Warning(
                    "{!r} for {!r} could not be imported.".format(module, app_label),
                    id='migrations.W001',
                )
            )
    return warnings
