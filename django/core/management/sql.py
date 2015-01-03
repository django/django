from __future__ import unicode_literals

import io
import os
import re
import warnings

from django.apps import apps
from django.conf import settings
from django.core.management.base import CommandError
from django.db import models, router
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.version import get_docs_version


def check_for_migrations(app_config, connection):
    # Inner import, else tests imports it too early as it needs settings
    from django.db.migrations.loader import MigrationLoader
    loader = MigrationLoader(connection)
    if app_config.label in loader.migrated_apps:
        raise CommandError(
            "App '%s' has migrations. Only the sqlmigrate and sqlflush commands "
            "can be used when an app has migrations." % app_config.label
        )


def sql_create(app_config, style, connection):
    "Returns a list of the CREATE TABLE SQL statements for the given app."

    check_for_migrations(app_config, connection)

    if connection.settings_dict['ENGINE'] == 'django.db.backends.dummy':
        # This must be the "dummy" database backend, which means the user
        # hasn't set ENGINE for the database.
        raise CommandError(
            "Django doesn't know which syntax to use for your SQL statements,\n"
            "because you haven't properly specified the ENGINE setting for the database.\n"
            "see: https://docs.djangoproject.com/en/%s/ref/settings/#databases" % get_docs_version()
        )

    # Get installed models, so we generate REFERENCES right.
    # We trim models from the current app so that the sqlreset command does not
    # generate invalid SQL (leaving models out of known_models is harmless, so
    # we can be conservative).
    app_models = list(app_config.get_models(include_auto_created=True))
    final_output = []
    tables = connection.introspection.table_names()
    known_models = set(model for model in connection.introspection.installed_models(tables) if model not in app_models)
    pending_references = {}

    for model in router.get_migratable_models(app_config, connection.alias, include_auto_created=True):
        output, references = connection.creation.sql_create_model(model, style, known_models)
        final_output.extend(output)
        for refto, refs in references.items():
            pending_references.setdefault(refto, []).extend(refs)
            if refto in known_models:
                final_output.extend(connection.creation.sql_for_pending_references(refto, style, pending_references))
        final_output.extend(connection.creation.sql_for_pending_references(model, style, pending_references))
        # Keep track of the fact that we've created the table for this model.
        known_models.add(model)

    # Handle references to tables that are from other apps
    # but don't exist physically.
    not_installed_models = set(pending_references.keys())
    if not_installed_models:
        alter_sql = []
        for model in not_installed_models:
            alter_sql.extend('-- ' + sql for sql in
                connection.creation.sql_for_pending_references(model, style, pending_references))
        if alter_sql:
            final_output.append('-- The following references should be added but depend on non-existent tables:')
            final_output.extend(alter_sql)

    return final_output


def sql_delete(app_config, style, connection, close_connection=True):
    "Returns a list of the DROP TABLE SQL statements for the given app."

    check_for_migrations(app_config, connection)

    # This should work even if a connection isn't available
    try:
        cursor = connection.cursor()
    except Exception:
        cursor = None

    try:
        # Figure out which tables already exist
        if cursor:
            table_names = connection.introspection.table_names(cursor)
        else:
            table_names = []

        output = []

        # Output DROP TABLE statements for standard application tables.
        to_delete = set()

        references_to_delete = {}
        app_models = router.get_migratable_models(app_config, connection.alias, include_auto_created=True)
        for model in app_models:
            if cursor and connection.introspection.table_name_converter(model._meta.db_table) in table_names:
                # The table exists, so it needs to be dropped
                opts = model._meta
                for f in opts.local_fields:
                    if f.rel and f.rel.to not in to_delete:
                        references_to_delete.setdefault(f.rel.to, []).append((model, f))

                to_delete.add(model)

        for model in app_models:
            if connection.introspection.table_name_converter(model._meta.db_table) in table_names:
                output.extend(connection.creation.sql_destroy_model(model, references_to_delete, style))
    finally:
        # Close database connection explicitly, in case this output is being piped
        # directly into a database client, to avoid locking issues.
        if cursor and close_connection:
            cursor.close()
            connection.close()

    if not output:
        output.append('-- App creates no tables in the database. Nothing to do.')
    return output[::-1]  # Reverse it, to deal with table dependencies.


def sql_flush(style, connection, only_django=False, reset_sequences=True, allow_cascade=False):
    """
    Returns a list of the SQL statements used to flush the database.

    If only_django is True, then only table names that have associated Django
    models and are in INSTALLED_APPS will be included.
    """
    if only_django:
        tables = connection.introspection.django_table_names(only_existing=True, include_views=False)
    else:
        tables = connection.introspection.table_names(include_views=False)
    seqs = connection.introspection.sequence_list() if reset_sequences else ()
    statements = connection.ops.sql_flush(style, tables, seqs, allow_cascade)
    return statements


def sql_custom(app_config, style, connection):
    "Returns a list of the custom table modifying SQL statements for the given app."

    check_for_migrations(app_config, connection)

    output = []

    app_models = router.get_migratable_models(app_config, connection.alias)

    for model in app_models:
        output.extend(custom_sql_for_model(model, style, connection))

    return output


def sql_indexes(app_config, style, connection):
    "Returns a list of the CREATE INDEX SQL statements for all models in the given app."

    check_for_migrations(app_config, connection)

    output = []
    for model in router.get_migratable_models(app_config, connection.alias, include_auto_created=True):
        output.extend(connection.creation.sql_indexes_for_model(model, style))
    return output


def sql_destroy_indexes(app_config, style, connection):
    "Returns a list of the DROP INDEX SQL statements for all models in the given app."

    check_for_migrations(app_config, connection)

    output = []
    for model in router.get_migratable_models(app_config, connection.alias, include_auto_created=True):
        output.extend(connection.creation.sql_destroy_indexes_for_model(model, style))
    return output


def sql_all(app_config, style, connection):

    check_for_migrations(app_config, connection)

    "Returns a list of CREATE TABLE SQL, initial-data inserts, and CREATE INDEX SQL for the given module."
    return (
        sql_create(app_config, style, connection) +
        sql_custom(app_config, style, connection) +
        sql_indexes(app_config, style, connection)
    )


def _split_statements(content):
    # Private API only called from code that emits a RemovedInDjango19Warning.
    comment_re = re.compile(r"^((?:'[^']*'|[^'])*?)--.*$")
    statements = []
    statement = []
    for line in content.split("\n"):
        cleaned_line = comment_re.sub(r"\1", line).strip()
        if not cleaned_line:
            continue
        statement.append(cleaned_line)
        if cleaned_line.endswith(";"):
            statements.append(" ".join(statement))
            statement = []
    return statements


def custom_sql_for_model(model, style, connection):
    opts = model._meta
    app_dirs = []
    app_dir = apps.get_app_config(model._meta.app_label).path
    app_dirs.append(os.path.normpath(os.path.join(app_dir, 'sql')))

    # Deprecated location -- remove in Django 1.9
    old_app_dir = os.path.normpath(os.path.join(app_dir, 'models/sql'))
    if os.path.exists(old_app_dir):
        warnings.warn("Custom SQL location '<app_label>/models/sql' is "
                      "deprecated, use '<app_label>/sql' instead.",
                      RemovedInDjango19Warning)
        app_dirs.append(old_app_dir)

    output = []

    # Post-creation SQL should come before any initial SQL data is loaded.
    # However, this should not be done for models that are unmanaged or
    # for fields that are part of a parent model (via model inheritance).
    if opts.managed:
        post_sql_fields = [f for f in opts.local_fields if hasattr(f, 'post_create_sql')]
        for f in post_sql_fields:
            output.extend(f.post_create_sql(style, model._meta.db_table))

    # Find custom SQL, if it's available.
    backend_name = connection.settings_dict['ENGINE'].split('.')[-1]
    sql_files = []
    for app_dir in app_dirs:
        sql_files.append(os.path.join(app_dir, "%s.%s.sql" % (opts.model_name, backend_name)))
        sql_files.append(os.path.join(app_dir, "%s.sql" % opts.model_name))
    for sql_file in sql_files:
        if os.path.exists(sql_file):
            with io.open(sql_file, encoding=settings.FILE_CHARSET) as fp:
                output.extend(connection.ops.prepare_sql_script(fp.read(), _allow_fallback=True))
    return output


def emit_pre_migrate_signal(create_models, verbosity, interactive, db):
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
            using=db)
        # For backwards-compatibility -- remove in Django 1.9.
        models.signals.pre_syncdb.send(
            sender=app_config.models_module,
            app=app_config.models_module,
            create_models=create_models,
            verbosity=verbosity,
            interactive=interactive,
            db=db)


def emit_post_migrate_signal(created_models, verbosity, interactive, db):
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
            using=db)
        # For backwards-compatibility -- remove in Django 1.9.
        models.signals.post_syncdb.send(
            sender=app_config.models_module,
            app=app_config.models_module,
            created_models=created_models,
            verbosity=verbosity,
            interactive=interactive,
            db=db)
