# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

from . import Warning, register


@register('migrations')
def check_migrations(app_configs=None, **kwargs):
    """
    Checks to see if the set of migrations on disk matches the
    migrations in the database. Prints a warning if they don't match.
    """
    from django.db import connections, DEFAULT_DB_ALIAS
    from django.db.migrations.executor import MigrationExecutor

    errors = []
    plan = None
    if settings.DATABASES:
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        errors.append(
            Warning(
                "You have unapplied migrations; "
                "your app may not work properly until they are applied.",
                hint="Run 'python manage.py migrate' to apply them.",
            )
        )
    return errors
