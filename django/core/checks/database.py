from itertools import chain

from django.apps import apps
from django.db import connections, router

from . import Tags, register


@register(Tags.database)
def check_database_backends(app_configs=None, databases=None, **kwargs):
    if databases is None:
        return []
    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(app_config.get_models() for app_config in app_configs)
    issues = []
    for alias in databases:
        conn = connections[alias]
        issues.extend(conn.validation.check(**kwargs))
    for model in models:
        for alias in databases:
            conn = connections[alias]
            if not router.allow_migrate_model(conn.alias, model):
                continue
            issues.extend(conn.validation.check_model(model, **kwargs))
    return issues
