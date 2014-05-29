from __future__ import unicode_literals

import codecs
import os
import re
import warnings

from django.apps import apps
from django.conf import settings
from django.core.management.base import CommandError
from django.db import models, router
from django.utils.deprecation import RemovedInDjango19Warning
from django.db.migrations.loader import MigrationLoader


def check_for_migrations(app_config, connection):
    loader = MigrationLoader(connection)

    if app_config.label in loader.migrated_apps:
        raise CommandError("App '%s' has migrations. Only the sqlmigrate and sqlflush commands can be used when an app has migrations." % app_config.label)


def sql_create(app_config, connection):
    "Returns a list of the CREATE TABLE SQL statements for the given app."

    check_for_migrations(app_config, connection)

    if connection.settings_dict['ENGINE'] == 'django.db.backends.dummy':
        # This must be the "dummy" database backend, which means the user
        # hasn't set ENGINE for the database.
        raise CommandError("Django doesn't know which syntax to use for your SQL statements,\n" +
            "because you haven't properly specified the ENGINE setting for the database.\n" +
            "see: https://docs.djangoproject.com/en/dev/ref/settings/#databases")

    # Get installed models, so we generate REFERENCES right.
    # We trim models from the current app so that the sqlreset command does not
    # generate invalid SQL (leaving models out of known_models is harmless, so
    # we can be conservative).
    app_models = app_config.get_models(include_auto_created=True)

    with connection.schema_editor(collect_sql=True) as schema_editor:
        for model in router.get_migratable_models(app_config, connection.alias):
            schema_editor.create_model(model)

    return schema_editor.collected_sql


def sql_delete(app_config, connection):
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

        app_models = router.get_migratable_models(app_config, connection.alias)

        with connection.schema_editor(collect_sql=True) as schema_editor:
            for model in app_models:
                if connection.introspection.table_name_converter(model._meta.db_table) in table_names:
                    schema_editor.delete_model(model)

        output.extend(schema_editor.collected_sql)

    finally:
        # Close database connection explicitly, in case this output is being piped
        # directly into a database client, to avoid locking issues.
        if cursor:
            cursor.close()
            connection.close()

    return output[::-1]  # Reverse it, to deal with table dependencies.


def sql_flush(style, connection, only_django=False, reset_sequences=True, allow_cascade=False):
    """
    Returns a list of the SQL statements used to flush the database.

    If only_django is True, then only table names that have associated Django
    models and are in INSTALLED_APPS will be included.
    """

    if only_django:
        tables = connection.introspection.django_table_names(only_existing=True)
    else:
        tables = connection.introspection.table_names()
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
    "Returns a list of CREATE TABLE SQL, initial-data inserts, and CREATE INDEX SQL for the given module."

    check_for_migrations(app_config, connection)

    return sql_create(app_config, connection) + sql_custom(app_config, style, connection)


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
            with codecs.open(sql_file, 'r', encoding=settings.FILE_CHARSET) as fp:
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
