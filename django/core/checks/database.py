from django.db import connections

from . import Tags, register


@register(Tags.database)
def check_database_backends(*args, **kwargs):
    issues = []
    for conn in connections.all():
        issues.extend(conn.validation.check(**kwargs))
    return issues
