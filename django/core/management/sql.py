import os
import re

from django.conf import settings
from django.core.management.base import CommandError
from django.db import models
from django.db.models import get_models

def sql_create(app, style, connection):
    "Returns a list of the CREATE TABLE SQL statements for the given app."

    if connection.settings_dict['ENGINE'] == 'django.db.backends.dummy':
        # This must be the "dummy" database backend, which means the user
        # hasn't set ENGINE for the databse.
        raise CommandError("Django doesn't know which syntax to use for your SQL statements,\n" +
            "because you haven't specified the ENGINE setting for the database.\n" +
            "Edit your settings file and change DATBASES['default']['ENGINE'] to something like\n" +
            "'django.db.backends.postgresql' or 'django.db.backends.mysql'.")

    # Get installed models, so we generate REFERENCES right.
    # We trim models from the current app so that the sqlreset command does not
    # generate invalid SQL (leaving models out of known_models is harmless, so
    # we can be conservative).
    app_models = models.get_models(app, include_auto_created=True)
    final_output = []
    tables = connection.introspection.table_names()
    known_models = set([model for model in connection.introspection.installed_models(tables) if model not in app_models])
    pending_references = {}

    for model in app_models:
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
            alter_sql.extend(['-- ' + sql for sql in
                connection.creation.sql_for_pending_references(model, style, pending_references)])
        if alter_sql:
            final_output.append('-- The following references should be added but depend on non-existent tables:')
            final_output.extend(alter_sql)

    return final_output

def sql_delete(app, style, connection):
    "Returns a list of the DROP TABLE SQL statements for the given app."

    # This should work even if a connection isn't available
    try:
        cursor = connection.cursor()
    except:
        cursor = None

    # Figure out which tables already exist
    if cursor:
        table_names = connection.introspection.get_table_list(cursor)
    else:
        table_names = []

    output = []

    # Output DROP TABLE statements for standard application tables.
    to_delete = set()

    references_to_delete = {}
    app_models = models.get_models(app, include_auto_created=True)
    for model in app_models:
        if cursor and connection.introspection.table_name_converter(model._meta.db_table) in table_names:
            # The table exists, so it needs to be dropped
            opts = model._meta
            for f in opts.local_fields:
                if f.rel and f.rel.to not in to_delete:
                    references_to_delete.setdefault(f.rel.to, []).append( (model, f) )

            to_delete.add(model)

    for model in app_models:
        if connection.introspection.table_name_converter(model._meta.db_table) in table_names:
            output.extend(connection.creation.sql_destroy_model(model, references_to_delete, style))

    # Close database connection explicitly, in case this output is being piped
    # directly into a database client, to avoid locking issues.
    if cursor:
        cursor.close()
        connection.close()

    return output[::-1] # Reverse it, to deal with table dependencies.

def sql_reset(app, style, connection):
    "Returns a list of the DROP TABLE SQL, then the CREATE TABLE SQL, for the given module."
    return sql_delete(app, style, connection) + sql_all(app, style, connection)

def sql_flush(style, connection, only_django=False):
    """
    Returns a list of the SQL statements used to flush the database.

    If only_django is True, then only table names that have associated Django
    models and are in INSTALLED_APPS will be included.
    """
    if only_django:
        tables = connection.introspection.django_table_names(only_existing=True)
    else:
        tables = connection.introspection.table_names()
    statements = connection.ops.sql_flush(
        style, tables, connection.introspection.sequence_list()
    )
    return statements

def sql_custom(app, style, connection):
    "Returns a list of the custom table modifying SQL statements for the given app."
    output = []

    app_models = get_models(app)
    app_dir = os.path.normpath(os.path.join(os.path.dirname(app.__file__), 'sql'))

    for model in app_models:
        output.extend(custom_sql_for_model(model, style, connection))

    return output

def sql_indexes(app, style, connection):
    "Returns a list of the CREATE INDEX SQL statements for all models in the given app."
    output = []
    for model in models.get_models(app):
        output.extend(connection.creation.sql_indexes_for_model(model, style))
    return output

def sql_all(app, style, connection):
    "Returns a list of CREATE TABLE SQL, initial-data inserts, and CREATE INDEX SQL for the given module."
    return sql_create(app, style, connection) + sql_custom(app, style, connection) + sql_indexes(app, style, connection)

def custom_sql_for_model(model, style, connection):
    opts = model._meta
    app_dir = os.path.normpath(os.path.join(os.path.dirname(models.get_app(model._meta.app_label).__file__), 'sql'))
    output = []

    # Post-creation SQL should come before any initial SQL data is loaded.
    # However, this should not be done for models that are unmanaged or
    # for fields that are part of a parent model (via model inheritance).
    if opts.managed:
        post_sql_fields = [f for f in opts.local_fields if hasattr(f, 'post_create_sql')]
        for f in post_sql_fields:
            output.extend(f.post_create_sql(style, model._meta.db_table))

    # Some backends can't execute more than one SQL statement at a time,
    # so split into separate statements.
    statements = re.compile(r";[ \t]*$", re.M)

    # Find custom SQL, if it's available.
    backend_name = connection.settings_dict['ENGINE'].split('.')[-1]
    sql_files = [os.path.join(app_dir, "%s.%s.sql" % (opts.object_name.lower(), backend_name)),
                 os.path.join(app_dir, "%s.sql" % opts.object_name.lower())]
    for sql_file in sql_files:
        if os.path.exists(sql_file):
            fp = open(sql_file, 'U')
            for statement in statements.split(fp.read().decode(settings.FILE_CHARSET)):
                # Remove any comments from the file
                statement = re.sub(ur"--.*([\n\Z]|$)", "", statement)
                if statement.strip():
                    output.append(statement + u";")
            fp.close()

    return output


def emit_post_sync_signal(created_models, verbosity, interactive, db):
    # Emit the post_sync signal for every application.
    for app in models.get_apps():
        app_name = app.__name__.split('.')[-2]
        if verbosity >= 2:
            print "Running post-sync handlers for application", app_name
        models.signals.post_syncdb.send(sender=app, app=app,
            created_models=created_models, verbosity=verbosity,
            interactive=interactive, db=db)
