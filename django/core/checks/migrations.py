from django.core.checks import Tags, register
from django.db import connections


@register(Tags.migrations)
def check_migration_operations(databases=None, **kwargs):
    from django.db.migrations.executor import MigrationExecutor

    if databases is None:
        return []

    errors = []
    for alias in databases:
        connection = connections[alias]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        for migration, _ in executor.migration_plan(targets):
            errors.extend(migration.check())
    return errors
