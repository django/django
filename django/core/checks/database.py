from itertools import chain

from django.apps import apps
from django.db import connections, router

from . import Tags, register


@register(Tags.database)
def check_database_backends(app_configs=None, **kwargs):
    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(app_config.get_models() for app_config in app_configs)
    issues = []
    for conn in connections.all():
        issues.extend(conn.validation.check(**kwargs))
    for model in models:
        for conn in connections.all():
            if not router.allow_migrate_model(conn.alias, model):
                continue
            issues.extend(conn.validation.check_model(model, **kwargs))
    return issues
