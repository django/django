from django.apps import apps
from django.db import models


def sql_flush(style, connection, only_django=False, reset_sequences=True, allow_cascade=False):
    """
    Return a list of the SQL statements used to flush the database.

    If only_django is True, only include the table names that have associated
    Django models and are in INSTALLED_APPS .
    """
    if only_django:
        tables = connection.introspection.django_table_names(only_existing=True, include_views=False)
    else:
        tables = connection.introspection.table_names(include_views=False)
    seqs = connection.introspection.sequence_list() if reset_sequences else ()
    return connection.ops.sql_flush(style, tables, seqs, allow_cascade)


def emit_pre_migrate_signal(verbosity, interactive, db, **kwargs):
    # Emit the pre_migrate signal for every application.
    for app_config in apps.get_app_configs():
        if app_config.models_module is None:
            continue
        if verbosity >= 2:
            print("Running pre-migrate handlers for application %s" % app_config.label)
        models.signals.pre_migrate.send(
            sender=app_config,
            app_config=app_config,
            verbosity=verbosity,
            interactive=interactive,
            using=db,
            **kwargs
        )


def emit_post_migrate_signal(verbosity, interactive, db, **kwargs):
    # Emit the post_migrate signal for every application.
    for app_config in apps.get_app_configs():
        if app_config.models_module is None:
            continue
        if verbosity >= 2:
            print("Running post-migrate handlers for application %s" % app_config.label)
        models.signals.post_migrate.send(
            sender=app_config,
            app_config=app_config,
            verbosity=verbosity,
            interactive=interactive,
            using=db,
            **kwargs
        )
