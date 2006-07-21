# Django management-related functions, including "CREATE TABLE" generation and
# development-server initialization.

import django
from django.core.exceptions import ImproperlyConfigured
import os, re, shutil, sys, textwrap
from optparse import OptionParser
from django.utils import termcolors

# For Python 2.3
if not hasattr(__builtins__, 'set'):
    from sets import Set as set

MODULE_TEMPLATE = '''    {%% if perms.%(app)s.%(addperm)s or perms.%(app)s.%(changeperm)s %%}
    <tr>
        <th>{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/">{%% endif %%}%(name)s{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</th>
        <td class="x50">{%% if perms.%(app)s.%(addperm)s %%}<a href="%(app)s/%(mod)s/add/" class="addlink">{%% endif %%}Add{%% if perms.%(app)s.%(addperm)s %%}</a>{%% endif %%}</td>
        <td class="x75">{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/" class="changelink">{%% endif %%}Change{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</td>
    </tr>
    {%% endif %%}'''

APP_ARGS = '[appname ...]'

# Use django.__path__[0] because we don't know which directory django into
# which has been installed.
PROJECT_TEMPLATE_DIR = os.path.join(django.__path__[0], 'conf', '%s_template')

INVALID_PROJECT_NAMES = ('django', 'test')

# Set up the terminal color scheme.
class dummy: pass
style = dummy()
style.ERROR = termcolors.make_style(fg='red', opts=('bold',))
style.ERROR_OUTPUT = termcolors.make_style(fg='red', opts=('bold',))
style.SQL_FIELD = termcolors.make_style(fg='green', opts=('bold',))
style.SQL_COLTYPE = termcolors.make_style(fg='green')
style.SQL_KEYWORD = termcolors.make_style(fg='yellow')
style.SQL_TABLE = termcolors.make_style(opts=('bold',))
del dummy

def disable_termcolors():
    class dummy:
        def __getattr__(self, attr):
            return lambda x: x
    global style
    style = dummy()

# Disable terminal coloring on Windows, Pocket PC, or if somebody's piping the output.
if sys.platform == 'win32' or sys.platform == 'Pocket PC' or not sys.stdout.isatty():
    disable_termcolors()

def _is_valid_dir_name(s):
    return bool(re.search(r'^\w+$', s))

def _get_installed_models(table_list):
    "Gets a set of all models that are installed, given a list of existing tables"
    from django.db import models
    all_models = []
    for app in models.get_apps():
        for model in models.get_models(app):
            all_models.append(model)
    return set([m for m in all_models if m._meta.db_table in table_list])

def _get_table_list():
    "Gets a list of all db tables that are physically installed."
    from django.db import connection, get_introspection_module
    cursor = connection.cursor()
    return get_introspection_module().get_table_list(cursor)

# If the foreign key points to an AutoField, a PositiveIntegerField or a
# PositiveSmallIntegerField, the foreign key should be an IntegerField, not the
# referred field type. Otherwise, the foreign key should be the same type of
# field as the field to which it points.
get_rel_data_type = lambda f: (f.get_internal_type() in ('AutoField', 'PositiveIntegerField', 'PositiveSmallIntegerField')) and 'IntegerField' or f.get_internal_type()

def get_version():
    "Returns the version as a human-format string."
    from django import VERSION
    v = '.'.join([str(i) for i in VERSION[:-1]])
    if VERSION[-1]:
        v += ' (%s)' % VERSION[-1]
    return v

def get_sql_create(app):
    "Returns a list of the CREATE TABLE SQL statements for the given app."
    from django.db import get_creation_module, models
    data_types = get_creation_module().DATA_TYPES

    if not data_types:
        # This must be the "dummy" database backend, which means the user
        # hasn't set DATABASE_ENGINE.
        sys.stderr.write(style.ERROR("Error: Django doesn't know which syntax to use for your SQL statements,\n" +
            "because you haven't specified the DATABASE_ENGINE setting.\n" +
            "Edit your settings file and change DATABASE_ENGINE to something like 'postgresql' or 'mysql'.\n"))
        sys.exit(1)

    # Get installed models, so we generate REFERENCES right
    final_output = []
    known_models = set(_get_installed_models(_get_table_list()))
    pending_references = {}

    app_models = models.get_models(app)

    for model in app_models:
        output, references = _get_sql_model_create(model, known_models)
        final_output.extend(output)
        for refto, refs in references.items():
            pending_references.set_default(refto,[]).extend(refs)
        final_output.extend(_get_sql_for_pending_references(model, pending_references))
        # Keep track of the fact that we've created the table for this model.
        known_models.add(model)

    # Create the many-to-many join tables.
    for model in app_models:
        final_output.extend(_get_many_to_many_sql_for_model(model))

    # Handle references to tables that are from other apps
    # but don't exist physically
    not_installed_models = set(pending_references.keys())
    if not_installed_models:
        final_output.append('-- The following references should be added but depend on non-existant tables:')
        for model in not_installed_models:
            final_output.extend(['-- ' + sql for sql in
                _get_sql_for_pending_references(model, pending_references)])

    return final_output
get_sql_create.help_doc = "Prints the CREATE TABLE SQL statements for the given app name(s)."
get_sql_create.args = APP_ARGS

def _get_sql_model_create(model, known_models=set()):
    """
    Get the SQL required to create a single model.

    Returns list_of_sql, pending_references_dict
    """
    from django.db import backend, get_creation_module, models
    data_types = get_creation_module().DATA_TYPES

    opts = model._meta
    final_output = []
    table_output = []
    pending_references = {}
    for f in opts.fields:
        if isinstance(f, models.ForeignKey):
            rel_field = f.rel.get_related_field()
            data_type = get_rel_data_type(rel_field)
        else:
            rel_field = f
            data_type = f.get_internal_type()
        col_type = data_types[data_type]
        if col_type is not None:
            # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
            field_output = [style.SQL_FIELD(backend.quote_name(f.column)),
                style.SQL_COLTYPE(col_type % rel_field.__dict__)]
            field_output.append(style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or '')))
            if f.unique:
                field_output.append(style.SQL_KEYWORD('UNIQUE'))
            if f.primary_key:
                field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
            if f.rel:
                if f.rel.to in known_models:
                    field_output.append(style.SQL_KEYWORD('REFERENCES') + ' ' + \
                        style.SQL_TABLE(backend.quote_name(f.rel.to._meta.db_table)) + ' (' + \
                        style.SQL_FIELD(backend.quote_name(f.rel.to._meta.get_field(f.rel.field_name).column)) + ')'
                    )
                else:
                    # We haven't yet created the table to which this field
                    # is related, so save it for later.
                    pr = pending_references.setdefault(f.rel.to, []).append((model, f))
            table_output.append(' '.join(field_output))
    if opts.order_with_respect_to:
        table_output.append(style.SQL_FIELD(backend.quote_name('_order')) + ' ' + \
            style.SQL_COLTYPE(data_types['IntegerField']) + ' ' + \
            style.SQL_KEYWORD('NULL'))
    for field_constraints in opts.unique_together:
        table_output.append(style.SQL_KEYWORD('UNIQUE') + ' (%s)' % \
            ", ".join([backend.quote_name(style.SQL_FIELD(opts.get_field(f).column)) for f in field_constraints]))

    full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' + style.SQL_TABLE(backend.quote_name(opts.db_table)) + ' (']
    for i, line in enumerate(table_output): # Combine and add commas.
        full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
    full_statement.append(');')
    final_output.append('\n'.join(full_statement))

    return final_output, pending_references

def _get_sql_for_pending_references(model, pending_references):
    """
    Get any ALTER TABLE statements to add constraints after the fact.
    """
    from django.db import backend, get_creation_module
    data_types = get_creation_module().DATA_TYPES

    final_output = []
    reference_names = {}
    if backend.supports_constraints:
        opts = model._meta
        if model in pending_references:
            for rel_class, f in pending_references[model]:
                rel_opts = rel_class._meta
                r_table = rel_opts.db_table
                r_col = f.column
                table = opts.db_table
                col = opts.get_field(f.rel.field_name).column
                r_name = '%s_referencing_%s_%s' % (r_col, table, col)
                if r_name in reference_names:
                    reference_names[r_name] += 1
                    r_name += '_%s' % reference_names[r_name]
                else:
                    reference_names[r_name] = 0
                final_output.append(style.SQL_KEYWORD('ALTER TABLE') + ' %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s (%s);' % \
                    (backend.quote_name(r_table), r_name,
                    backend.quote_name(r_col), backend.quote_name(table), backend.quote_name(col)))
            del pending_references[model]
    return final_output

def _get_many_to_many_sql_for_model(model):
    from django.db import backend, get_creation_module
    from django.db.models import GenericRel
    
    data_types = get_creation_module().DATA_TYPES

    opts = model._meta
    final_output = []
    for f in opts.many_to_many:
        if not isinstance(f.rel, GenericRel):
            table_output = [style.SQL_KEYWORD('CREATE TABLE') + ' ' + \
                style.SQL_TABLE(backend.quote_name(f.m2m_db_table())) + ' (']
            table_output.append('    %s %s %s,' % \
                (style.SQL_FIELD(backend.quote_name('id')),
                style.SQL_COLTYPE(data_types['AutoField']),
                style.SQL_KEYWORD('NOT NULL PRIMARY KEY')))
            table_output.append('    %s %s %s %s (%s),' % \
                (style.SQL_FIELD(backend.quote_name(f.m2m_column_name())),
                style.SQL_COLTYPE(data_types[get_rel_data_type(opts.pk)] % opts.pk.__dict__),
                style.SQL_KEYWORD('NOT NULL REFERENCES'),
                style.SQL_TABLE(backend.quote_name(opts.db_table)),
                style.SQL_FIELD(backend.quote_name(opts.pk.column))))
            table_output.append('    %s %s %s %s (%s),' % \
                (style.SQL_FIELD(backend.quote_name(f.m2m_reverse_name())),
                style.SQL_COLTYPE(data_types[get_rel_data_type(f.rel.to._meta.pk)] % f.rel.to._meta.pk.__dict__),
                style.SQL_KEYWORD('NOT NULL REFERENCES'),
                style.SQL_TABLE(backend.quote_name(f.rel.to._meta.db_table)),
                style.SQL_FIELD(backend.quote_name(f.rel.to._meta.pk.column))))
            table_output.append('    %s (%s, %s)' % \
                (style.SQL_KEYWORD('UNIQUE'),
                style.SQL_FIELD(backend.quote_name(f.m2m_column_name())),
                style.SQL_FIELD(backend.quote_name(f.m2m_reverse_name()))))
            table_output.append(');')
            final_output.append('\n'.join(table_output))
    return final_output

def get_sql_delete(app):
    "Returns a list of the DROP TABLE SQL statements for the given app."
    from django.db import backend, connection, models, get_introspection_module
    introspection = get_introspection_module()

    # This should work even if a connecton isn't available
    try:
        cursor = connection.cursor()
    except:
        cursor = None

    # Figure out which tables already exist
    if cursor:
        table_names = introspection.get_table_list(cursor)
    else:
        table_names = []

    output = []

    # Output DROP TABLE statements for standard application tables.
    to_delete = set()

    references_to_delete = {}
    app_models = models.get_models(app)
    for model in app_models:
        if cursor and model._meta.db_table in table_names:
            # The table exists, so it needs to be dropped
            opts = model._meta
            for f in opts.fields:
                if f.rel and f.rel.to not in to_delete:
                    references_to_delete.setdefault(f.rel.to, []).append( (model, f) )

            to_delete.add(model)

    for model in app_models:
        if cursor and model._meta.db_table in table_names:
            # Drop the table now
            output.append('%s %s;' % (style.SQL_KEYWORD('DROP TABLE'),
                style.SQL_TABLE(backend.quote_name(model._meta.db_table))))
            if backend.supports_constraints and references_to_delete.has_key(model):
                for rel_class, f in references_to_delete[model]:
                    table = rel_class._meta.db_table
                    col = f.column
                    r_table = model._meta.db_table
                    r_col = model._meta.get_field(f.rel.field_name).column
                    output.append('%s %s %s %s;' % \
                        (style.SQL_KEYWORD('ALTER TABLE'),
                        style.SQL_TABLE(backend.quote_name(table)),
                        style.SQL_KEYWORD(backend.get_drop_foreignkey_sql()),
                        style.SQL_FIELD(backend.quote_name("%s_referencing_%s_%s" % (col, r_table, r_col)))))
                del references_to_delete[model]

    # Output DROP TABLE statements for many-to-many tables.
    for model in app_models:
        opts = model._meta
        for f in opts.many_to_many:
            if cursor and f.m2m_db_table() in table_names:
                output.append("%s %s;" % (style.SQL_KEYWORD('DROP TABLE'),
                    style.SQL_TABLE(backend.quote_name(f.m2m_db_table()))))

    app_label = app_models[0]._meta.app_label

    # Close database connection explicitly, in case this output is being piped
    # directly into a database client, to avoid locking issues.
    if cursor:
        cursor.close()
        connection.close()

    return output[::-1] # Reverse it, to deal with table dependencies.
get_sql_delete.help_doc = "Prints the DROP TABLE SQL statements for the given app name(s)."
get_sql_delete.args = APP_ARGS

def get_sql_reset(app):
    "Returns a list of the DROP TABLE SQL, then the CREATE TABLE SQL, for the given module."
    return get_sql_delete(app) + get_sql_all(app)
get_sql_reset.help_doc = "Prints the DROP TABLE SQL, then the CREATE TABLE SQL, for the given app name(s)."
get_sql_reset.args = APP_ARGS

def get_sql_initial_data_for_model(model):
    from django.db import models
    from django.conf import settings

    opts = model._meta
    app_dir = os.path.normpath(os.path.join(os.path.dirname(models.get_app(model._meta.app_label).__file__), 'sql'))
    output = []

    # Some backends can't execute more than one SQL statement at a time,
    # so split into separate statements.
    statements = re.compile(r";[ \t]*$", re.M)

    # Find custom SQL, if it's available.
    sql_files = [os.path.join(app_dir, "%s.%s.sql" % (opts.object_name.lower(), settings.DATABASE_ENGINE)),
                 os.path.join(app_dir, "%s.sql" % opts.object_name.lower())]
    for sql_file in sql_files:
        if os.path.exists(sql_file):
            fp = open(sql_file)
            for statement in statements.split(fp.read()):
                if statement.strip():
                    output.append(statement + ";")
            fp.close()

    return output

def get_sql_initial_data(app):
    "Returns a list of the initial INSERT SQL statements for the given app."
    from django.db.models import get_models
    output = []

    app_models = get_models(app)
    app_dir = os.path.normpath(os.path.join(os.path.dirname(app.__file__), 'sql'))

    for model in app_models:
        output.extend(get_sql_initial_data_for_model(model))

    return output
get_sql_initial_data.help_doc = "Prints the initial INSERT SQL statements for the given app name(s)."
get_sql_initial_data.args = APP_ARGS

def get_sql_sequence_reset(app):
    "Returns a list of the SQL statements to reset PostgreSQL sequences for the given app."
    from django.db import backend, models
    output = []
    for model in models.get_models(app):
        for f in model._meta.fields:
            if isinstance(f, models.AutoField):
                output.append("%s setval('%s', (%s max(%s) %s %s));" % \
                    (style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD('%s_%s_seq' % (model._meta.db_table, f.column)),
                    style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD(backend.quote_name(f.column)),
                    style.SQL_KEYWORD('FROM'),
                    style.SQL_TABLE(backend.quote_name(model._meta.db_table))))
                break # Only one AutoField is allowed per model, so don't bother continuing.
        for f in model._meta.many_to_many:
            output.append("%s setval('%s', (%s max(%s) %s %s));" % \
                (style.SQL_KEYWORD('SELECT'),
                style.SQL_FIELD('%s_id_seq' % f.m2m_db_table()),
                style.SQL_KEYWORD('SELECT'),
                style.SQL_FIELD(backend.quote_name('id')),
                style.SQL_KEYWORD('FROM'),
                style.SQL_TABLE(f.m2m_db_table())))
    return output
get_sql_sequence_reset.help_doc = "Prints the SQL statements for resetting PostgreSQL sequences for the given app name(s)."
get_sql_sequence_reset.args = APP_ARGS

def get_sql_indexes(app):
    "Returns a list of the CREATE INDEX SQL statements for the given app."
    from django.db import backend, models
    output = []

    for model in models.get_models(app):
        for f in model._meta.fields:
            if f.db_index:
                unique = f.unique and 'UNIQUE ' or ''
                output.append(
                    style.SQL_KEYWORD('CREATE %sINDEX' % unique) + ' ' + \
                    style.SQL_TABLE('%s_%s' % (model._meta.db_table, f.column)) + ' ' + \
                    style.SQL_KEYWORD('ON') + ' ' + \
                    style.SQL_TABLE(backend.quote_name(model._meta.db_table)) + ' ' + \
                    "(%s);" % style.SQL_FIELD(backend.quote_name(f.column))
                )
    return output
get_sql_indexes.help_doc = "Prints the CREATE INDEX SQL statements for the given model module name(s)."
get_sql_indexes.args = APP_ARGS

def get_sql_all(app):
    "Returns a list of CREATE TABLE SQL, initial-data inserts, and CREATE INDEX SQL for the given module."
    return get_sql_create(app) + get_sql_initial_data(app) + get_sql_indexes(app)
get_sql_all.help_doc = "Prints the CREATE TABLE, initial-data and CREATE INDEX SQL statements for the given model module name(s)."
get_sql_all.args = APP_ARGS

def syncdb():
    "Creates the database tables for all apps in INSTALLED_APPS whose tables haven't already been created."
    from django.db import connection, transaction, models, get_creation_module
    from django.db.models import signals
    from django.conf import settings
    from django.dispatch import dispatcher

    disable_termcolors()

    # First, try validating the models.
    _check_for_validation_errors()

    # Import the 'management' module within each installed app, to register
    # dispatcher events.
    for app_name in settings.INSTALLED_APPS:
        try:
            __import__(app_name + '.management', '', '', [''])
        except ImportError:
            pass

    data_types = get_creation_module().DATA_TYPES

    cursor = connection.cursor()

    # Get a list of all existing database tables,
    # so we know what needs to be added.
    table_list = _get_table_list()

    # Get a list of already installed *models* so that references work right.
    seen_models = _get_installed_models(table_list)
    created_models = set()
    pending_references = {}

    for app in models.get_apps():
        model_list = models.get_models(app)
        for model in model_list:
            # Create the model's database table, if it doesn't already exist.
            if model._meta.db_table in table_list:
                continue
            sql, references = _get_sql_model_create(model, seen_models)
            seen_models.add(model)
            created_models.add(model)
            for refto, refs in references.items():
                try:
                    pending_references[refto].extend(refs)
                except KeyError:
                    pending_references[refto] = refs
            sql.extend(_get_sql_for_pending_references(model, pending_references))
            print "Creating table %s" % model._meta.db_table
            for statement in sql:
                cursor.execute(statement)
            table_list.append(model._meta.db_table)

        for model in model_list:
            if model in created_models:
                sql = _get_many_to_many_sql_for_model(model)
                if sql:
                    print "Creating many-to-many tables for %s model" % model.__name__
                    for statement in sql:
                        cursor.execute(statement)

        transaction.commit_unless_managed()

    # Send the post_syncdb signal, so individual apps can do whatever they need
    # to do at this point.
    for app in models.get_apps():
        dispatcher.send(signal=signals.post_syncdb, sender=app,
            app=app, created_models=created_models)

        # Install initial data for the app (but only if this is a model we've
        # just created)
        for model in models.get_models(app):
            if model in created_models:
                initial_sql = get_sql_initial_data_for_model(model)
                if initial_sql:
                    print "Installing initial data for %s model" % model._meta.object_name
                    try:
                        for sql in initial_sql:
                            cursor.execute(sql)
                    except Exception, e:
                        sys.stderr.write("Failed to install initial SQL data for %s model: %s" % \
                                            (model._meta.object_name, e))
                        transaction.rollback_unless_managed()
                    else:
                        transaction.commit_unless_managed()

syncdb.args = ''

def get_admin_index(app):
    "Returns admin-index template snippet (in list form) for the given app."
    from django.utils.text import capfirst
    from django.db.models import get_models
    output = []
    app_models = get_models(app)
    app_label = app_models[0]._meta.app_label
    output.append('{%% if perms.%s %%}' % app_label)
    output.append('<div class="module"><h2>%s</h2><table>' % app_label.title())
    for model in app_models:
        if model._meta.admin:
            output.append(MODULE_TEMPLATE % {
                'app': app_label,
                'mod': model._meta.module_name,
                'name': capfirst(model._meta.verbose_name_plural),
                'addperm': model._meta.get_add_permission(),
                'changeperm': model._meta.get_change_permission(),
            })
    output.append('</table></div>')
    output.append('{% endif %}')
    return output
get_admin_index.help_doc = "Prints the admin-index template snippet for the given app name(s)."
get_admin_index.args = APP_ARGS

def _module_to_dict(module, omittable=lambda k: k.startswith('_')):
    "Converts a module namespace to a Python dictionary. Used by get_settings_diff."
    return dict([(k, repr(v)) for k, v in module.__dict__.items() if not omittable(k)])

def diffsettings():
    """
    Displays differences between the current settings.py and Django's
    default settings. Settings that don't appear in the defaults are
    followed by "###".
    """
    # Inspired by Postfix's "postconf -n".
    from django.conf import settings, global_settings

    user_settings = _module_to_dict(settings)
    default_settings = _module_to_dict(global_settings)

    output = []
    keys = user_settings.keys()
    keys.sort()
    for key in keys:
        if key not in default_settings:
            output.append("%s = %s  ###" % (key, user_settings[key]))
        elif user_settings[key] != default_settings[key]:
            output.append("%s = %s" % (key, user_settings[key]))
    print '\n'.join(output)
diffsettings.args = ""

def install(app):
    "Executes the equivalent of 'get_sql_all' in the current database."
    from django.db import connection, transaction

    app_name = app.__name__.split('.')[-2]

    disable_termcolors()

    # First, try validating the models.
    _check_for_validation_errors(app)

    sql_list = get_sql_all(app)

    try:
        cursor = connection.cursor()
        for sql in sql_list:
            cursor.execute(sql)
    except Exception, e:
        sys.stderr.write(style.ERROR("""Error: %s couldn't be installed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the database tables already exists.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlall %s'. That's the SQL this command wasn't able to run.
The full error: """ % (app_name, app_name)) + style.ERROR_OUTPUT(str(e)) + '\n')
        transaction.rollback_unless_managed()
        sys.exit(1)
    transaction.commit_unless_managed()
install.help_doc = "Executes ``sqlall`` for the given app(s) in the current database."
install.args = APP_ARGS

def reset(app):
    "Executes the equivalent of 'get_sql_reset' in the current database."
    from django.db import connection, transaction
    from cStringIO import StringIO
    app_name = app.__name__.split('.')[-2]

    disable_termcolors()

    # First, try validating the models.
    _check_for_validation_errors(app)
    sql_list = get_sql_reset(app)

    confirm = raw_input("""
You have requested a database reset.
This will IRREVERSIBLY DESTROY any data in your database.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
    if confirm == 'yes':
        try:
            cursor = connection.cursor()
            for sql in sql_list:
                cursor.execute(sql)
        except Exception, e:
            sys.stderr.write(style.ERROR("""Error: %s couldn't be installed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the database tables already exists.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlreset %s'. That's the SQL this command wasn't able to run.
The full error: """ % (app_name, app_name)) + style.ERROR_OUTPUT(str(e)) + '\n')
            transaction.rollback_unless_managed()
            sys.exit(1)
        transaction.commit_unless_managed()
    else:
        print "Reset cancelled."
reset.help_doc = "Executes ``sqlreset`` for the given app(s) in the current database."
reset.args = APP_ARGS

def _start_helper(app_or_project, name, directory, other_name=''):
    other = {'project': 'app', 'app': 'project'}[app_or_project]
    if not _is_valid_dir_name(name):
        sys.stderr.write(style.ERROR("Error: %r is not a valid %s name. Please use only numbers, letters and underscores.\n" % (name, app_or_project)))
        sys.exit(1)
    top_dir = os.path.join(directory, name)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        sys.stderr.write(style.ERROR("Error: %s\n" % e))
        sys.exit(1)
    template_dir = PROJECT_TEMPLATE_DIR % app_or_project
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:].replace('%s_name' % app_or_project, name)
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f.replace('%s_name' % app_or_project, name))
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ %s_name }}' % app_or_project, name).replace('{{ %s_name }}' % other, other_name))
            fp_old.close()
            fp_new.close()
            shutil.copymode(path_old, path_new)

def startproject(project_name, directory):
    "Creates a Django project for the given project_name in the given directory."
    from random import choice
    if project_name in INVALID_PROJECT_NAMES:
        sys.stderr.write(style.ERROR("Error: %r isn't a valid project name. Please try another.\n" % project_name))
        sys.exit(1)
    _start_helper('project', project_name, directory)
    # Create a random SECRET_KEY hash, and put it in the main settings.
    main_settings_file = os.path.join(directory, project_name, 'settings.py')
    settings_contents = open(main_settings_file, 'r').read()
    fp = open(main_settings_file, 'w')
    secret_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    settings_contents = re.sub(r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)
    fp.write(settings_contents)
    fp.close()
startproject.help_doc = "Creates a Django project directory structure for the given project name in the current directory."
startproject.args = "[projectname]"

def startapp(app_name, directory):
    "Creates a Django app for the given app_name in the given directory."
    # Determine the project_name a bit naively -- by looking at the name of
    # the parent directory.
    project_dir = os.path.normpath(os.path.join(directory, '..'))
    project_name = os.path.basename(project_dir)
    if app_name == os.path.basename(directory):
        sys.stderr.write(style.ERROR("Error: You cannot create an app with the same name (%r) as your project.\n" % app_name))
        sys.exit(1)
    _start_helper('app', app_name, directory, project_name)
startapp.help_doc = "Creates a Django app directory structure for the given app name in the current directory."
startapp.args = "[appname]"

def inspectdb():
    "Generator that introspects the tables in the given database name and returns a Django model, one line at a time."
    from django.db import connection, get_introspection_module
    from django.conf import settings
    import keyword

    introspection_module = get_introspection_module()

    def table2model(table_name):
        object_name = table_name.title().replace('_', '')
        return object_name.endswith('s') and object_name[:-1] or object_name

    cursor = connection.cursor()
    yield "# This is an auto-generated Django model module."
    yield "# You'll have to do the following manually to clean this up:"
    yield "#     * Rearrange models' order"
    yield "#     * Make sure each model has one field with primary_key=True"
    yield "# Feel free to rename the models, but don't rename db_table values or field names."
    yield "#"
    yield "# Also note: You'll have to insert the output of 'django-admin.py sqlinitialdata [appname]'"
    yield "# into your database."
    yield ''
    yield 'from django.db import models'
    yield ''
    for table_name in introspection_module.get_table_list(cursor):
        yield 'class %s(models.Model):' % table2model(table_name)
        try:
            relations = introspection_module.get_relations(cursor, table_name)
        except NotImplementedError:
            relations = {}
        try:
            indexes = introspection_module.get_indexes(cursor, table_name)
        except NotImplementedError:
            indexes = {}
        for i, row in enumerate(introspection_module.get_table_description(cursor, table_name)):
            att_name = row[0]
            comment_notes = [] # Holds Field notes, to be displayed in a Python comment.
            extra_params = {}  # Holds Field parameters such as 'db_column'.

            if keyword.iskeyword(att_name):
                extra_params['db_column'] = att_name
                att_name += '_field'
                comment_notes.append('Field renamed because it was a Python reserved word.')

            if relations.has_key(i):
                rel_to = relations[i][1] == table_name and "'self'" or table2model(relations[i][1])
                field_type = 'ForeignKey(%s' % rel_to
                if att_name.endswith('_id'):
                    att_name = att_name[:-3]
                else:
                    extra_params['db_column'] = att_name
            else:
                try:
                    field_type = introspection_module.DATA_TYPES_REVERSE[row[1]]
                except KeyError:
                    field_type = 'TextField'
                    comment_notes.append('This field type is a guess.')

                # This is a hook for DATA_TYPES_REVERSE to return a tuple of
                # (field_type, extra_params_dict).
                if type(field_type) is tuple:
                    field_type, new_params = field_type
                    extra_params.update(new_params)

                # Add maxlength for all CharFields.
                if field_type == 'CharField' and row[3]:
                    extra_params['maxlength'] = row[3]

                if field_type == 'FloatField':
                    extra_params['max_digits'] = row[4]
                    extra_params['decimal_places'] = row[5]

                # Add primary_key and unique, if necessary.
                column_name = extra_params.get('db_column', att_name)
                if column_name in indexes:
                    if indexes[column_name]['primary_key']:
                        extra_params['primary_key'] = True
                    elif indexes[column_name]['unique']:
                        extra_params['unique'] = True

                field_type += '('

            # Don't output 'id = meta.AutoField(primary_key=True)', because
            # that's assumed if it doesn't exist.
            if att_name == 'id' and field_type == 'AutoField(' and extra_params == {'primary_key': True}:
                continue

            # Add 'null' and 'blank', if the 'null_ok' flag was present in the
            # table description.
            if row[6]: # If it's NULL...
                extra_params['blank'] = True
                if not field_type in ('TextField(', 'CharField('):
                    extra_params['null'] = True

            field_desc = '%s = models.%s' % (att_name, field_type)
            if extra_params:
                if not field_desc.endswith('('):
                    field_desc += ', '
                field_desc += ', '.join(['%s=%r' % (k, v) for k, v in extra_params.items()])
            field_desc += ')'
            if comment_notes:
                field_desc += ' # ' + ' '.join(comment_notes)
            yield '    %s' % field_desc
        yield '    class Meta:'
        yield '        db_table = %r' % table_name
        yield ''
inspectdb.help_doc = "Introspects the database tables in the given database and outputs a Django model module."
inspectdb.args = ""

class ModelErrorCollection:
    def __init__(self, outfile=sys.stdout):
        self.errors = []
        self.outfile = outfile

    def add(self, context, error):
        self.errors.append((context, error))
        self.outfile.write(style.ERROR("%s: %s\n" % (context, error)))

def get_validation_errors(outfile, app=None):
    """
    Validates all models that are part of the specified app. If no app name is provided,
    validates all models of all installed apps. Writes errors, if any, to outfile.
    Returns number of errors.
    """
    from django.db import models
    from django.db.models.loading import get_app_errors
    from django.db.models.fields.related import RelatedObject

    e = ModelErrorCollection(outfile)
    
    for (app_name, error) in get_app_errors().items():
        e.add(app_name, error)
        
    for cls in models.get_models(app):
        opts = cls._meta

        # Do field-specific validation.
        for f in opts.fields:
            if f.name == 'id' and not f.primary_key and opts.pk.name == 'id':
                e.add(opts, '"%s": You can\'t use "id" as a field name, because each model automatically gets an "id" field if none of the fields have primary_key=True. You need to either remove/rename your "id" field or add primary_key=True to a field.' % f.name)
            if isinstance(f, models.CharField) and f.maxlength in (None, 0):
                e.add(opts, '"%s": CharFields require a "maxlength" attribute.' % f.name)
            if isinstance(f, models.FloatField):
                if f.decimal_places is None:
                    e.add(opts, '"%s": FloatFields require a "decimal_places" attribute.' % f.name)
                if f.max_digits is None:
                    e.add(opts, '"%s": FloatFields require a "max_digits" attribute.' % f.name)
            if isinstance(f, models.FileField) and not f.upload_to:
                e.add(opts, '"%s": FileFields require an "upload_to" attribute.' % f.name)
            if isinstance(f, models.ImageField):
                try:
                    from PIL import Image
                except ImportError:
                    e.add(opts, '"%s": To use ImageFields, you need to install the Python Imaging Library. Get it at http://www.pythonware.com/products/pil/ .' % f.name)
            if f.prepopulate_from is not None and type(f.prepopulate_from) not in (list, tuple):
                e.add(opts, '"%s": prepopulate_from should be a list or tuple.' % f.name)
            if f.choices:
                if not hasattr(f.choices, '__iter__'):
                    e.add(opts, '"%s": "choices" should be iterable (e.g., a tuple or list).' % f.name)
                else:
                    for c in f.choices:
                        if not type(c) in (tuple, list) or len(c) != 2:
                            e.add(opts, '"%s": "choices" should be a sequence of two-tuples.' % f.name)
            if f.db_index not in (None, True, False):
                e.add(opts, '"%s": "db_index" should be either None, True or False.' % f.name)

            # Check to see if the related field will clash with any
            # existing fields, m2m fields, m2m related objects or related objects
            if f.rel:
                rel_opts = f.rel.to._meta
                if f.rel.to not in models.get_models():
                    e.add(opts, "'%s' has relation with model %s, which has not been installed" % (f.name, rel_opts.object_name))

                rel_name = RelatedObject(f.rel.to, cls, f).get_accessor_name()
                rel_query_name = f.related_query_name()
                for r in rel_opts.fields:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.many_to_many:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.get_all_related_many_to_many_objects():
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                for r in rel_opts.get_all_related_objects():
                    if r.field is not f:
                        if r.get_accessor_name() == rel_name:
                            e.add(opts, "Accessor for field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                        if r.get_accessor_name() == rel_query_name:
                            e.add(opts, "Reverse query name for field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))

                
        for i, f in enumerate(opts.many_to_many):
            # Check to see if the related m2m field will clash with any
            # existing fields, m2m fields, m2m related objects or related objects
            rel_opts = f.rel.to._meta
            if f.rel.to not in models.get_models():
                e.add(opts, "'%s' has m2m relation with model %s, which has not been installed" % (f.name, rel_opts.object_name))

            rel_name = RelatedObject(f.rel.to, cls, f).get_accessor_name()
            rel_query_name = f.related_query_name()
            for r in rel_opts.fields:
                if r.name == rel_name:
                    e.add(opts, "Accessor for m2m field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                if r.name == rel_query_name:
                    e.add(opts, "Reverse query name for m2m field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
            for r in rel_opts.many_to_many:
                if r.name == rel_name:
                    e.add(opts, "Accessor for m2m field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                if r.name == rel_query_name:
                    e.add(opts, "Reverse query name for m2m field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
            for r in rel_opts.get_all_related_many_to_many_objects():
                if r.field is not f:
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
            for r in rel_opts.get_all_related_objects():
                if r.get_accessor_name() == rel_name:
                    e.add(opts, "Accessor for m2m field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                if r.get_accessor_name() == rel_query_name:
                    e.add(opts, "Reverse query name for m2m field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))

        # Check admin attribute.
        if opts.admin is not None:
            if not isinstance(opts.admin, models.AdminOptions):
                e.add(opts, '"admin" attribute, if given, must be set to a models.AdminOptions() instance.')
            else:
                # list_display
                if not isinstance(opts.admin.list_display, (list, tuple)):
                    e.add(opts, '"admin.list_display", if given, must be set to a list or tuple.')
                else:
                    for fn in opts.admin.list_display:
                        try:
                            f = opts.get_field(fn)
                        except models.FieldDoesNotExist:
                            if not hasattr(cls, fn):
                                e.add(opts, '"admin.list_display" refers to %r, which isn\'t an attribute, method or property.' % fn)
                        else:
                            if isinstance(f, models.ManyToManyField):
                                e.add(opts, '"admin.list_display" doesn\'t support ManyToManyFields (%r).' % fn)
                # list_display_links
                if opts.admin.list_display_links and not opts.admin.list_display:
                    e.add(opts, '"admin.list_display" must be defined for "admin.list_display_links" to be used.')
                if not isinstance(opts.admin.list_display_links, (list, tuple)):
                    e.add(opts, '"admin.list_display_links", if given, must be set to a list or tuple.')
                else:
                    for fn in opts.admin.list_display_links:
                        try:
                            f = opts.get_field(fn)
                        except models.FieldDoesNotExist:
                            e.add(opts, '"admin.list_filter" refers to %r, which isn\'t a field.' % fn)
                        if fn not in opts.admin.list_display:
                            e.add(opts, '"admin.list_display_links" refers to %r, which is not defined in "admin.list_display".' % fn)
                # list_filter
                if not isinstance(opts.admin.list_filter, (list, tuple)):
                    e.add(opts, '"admin.list_filter", if given, must be set to a list or tuple.')
                else:
                    for fn in opts.admin.list_filter:
                        try:
                            f = opts.get_field(fn)
                        except models.FieldDoesNotExist:
                            e.add(opts, '"admin.list_filter" refers to %r, which isn\'t a field.' % fn)

        # Check ordering attribute.
        if opts.ordering:
            for field_name in opts.ordering:
                if field_name == '?': continue
                if field_name.startswith('-'):
                    field_name = field_name[1:]
                if opts.order_with_respect_to and field_name == '_order':
                    continue
                if '.' in field_name: continue # Skip ordering in the format 'table.field'.
                try:
                    opts.get_field(field_name, many_to_many=False)
                except models.FieldDoesNotExist:
                    e.add(opts, '"ordering" refers to "%s", a field that doesn\'t exist.' % field_name)

        # Check core=True, if needed.
        for related in opts.get_followed_related_objects():
            if not related.edit_inline:
                continue
            try:
                for f in related.opts.fields:
                    if f.core:
                        raise StopIteration
                e.add(related.opts, "At least one field in %s should have core=True, because it's being edited inline by %s.%s." % (related.opts.object_name, opts.module_name, opts.object_name))
            except StopIteration:
                pass

        # Check unique_together.
        for ut in opts.unique_together:
            for field_name in ut:
                try:
                    f = opts.get_field(field_name, many_to_many=True)
                except models.FieldDoesNotExist:
                    e.add(opts, '"unique_together" refers to %s, a field that doesn\'t exist. Check your syntax.' % field_name)
                else:
                    if isinstance(f.rel, models.ManyToManyRel):
                        e.add(opts, '"unique_together" refers to %s. ManyToManyFields are not supported in unique_together.' % f.name)

    return len(e.errors)

def validate(outfile=sys.stdout):
    "Validates all installed models."
    try:
        num_errors = get_validation_errors(outfile)
        outfile.write('%s error%s found.\n' % (num_errors, num_errors != 1 and 's' or ''))
    except ImproperlyConfigured:
        outfile.write("Skipping validation because things aren't configured properly.")
validate.args = ''

def _check_for_validation_errors(app=None):
    """Check that an app has no validation errors, and exit with errors if it does."""
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    s = StringIO()
    num_errors = get_validation_errors(s, app)
    if num_errors:
        if app:
            sys.stderr.write(style.ERROR("Error: %s couldn't be installed, because there were errors in your model:\n" % app))
        else:
            sys.stderr.write(style.ERROR("Error: Couldn't install apps, because there were errors in one or more models:\n"))
        s.seek(0)
        sys.stderr.write(s.read())
        sys.exit(1)

def runserver(addr, port, use_reloader=True):
    "Starts a lightweight Web server for development."
    from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
    from django.core.handlers.wsgi import WSGIHandler
    if not addr:
        addr = '127.0.0.1'
    if not port.isdigit():
        sys.stderr.write(style.ERROR("Error: %r is not a valid port number.\n" % port))
        sys.exit(1)
    quit_command = sys.platform == 'win32' and 'CTRL-BREAK' or 'CONTROL-C'
    def inner_run():
        from django.conf import settings
        print "Validating models..."
        validate()
        print "\nDjango version %s, using settings %r" % (get_version(), settings.SETTINGS_MODULE)
        print "Development server is running at http://%s:%s/" % (addr, port)
        print "Quit the server with %s." % quit_command
        try:
            run(addr, int(port), AdminMediaHandler(WSGIHandler()))
        except WSGIServerException, e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                13: "You don't have permission to access that port.",
                98: "That port is already in use.",
                99: "That IP address can't be assigned-to.",
            }
            try:
                error_text = ERRORS[e.args[0].args[0]]
            except (AttributeError, KeyError):
                error_text = str(e)
            sys.stderr.write(style.ERROR("Error: %s" % error_text) + '\n')
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(0)
    if use_reloader:
        from django.utils import autoreload
        autoreload.main(inner_run)
    else:
        inner_run()
runserver.args = '[--noreload] [optional port number, or ipaddr:port]'

def createcachetable(tablename):
    "Creates the table needed to use the SQL cache backend"
    from django.db import backend, connection, transaction, get_creation_module, models
    data_types = get_creation_module().DATA_TYPES
    fields = (
        # "key" is a reserved word in MySQL, so use "cache_key" instead.
        models.CharField(name='cache_key', maxlength=255, unique=True, primary_key=True),
        models.TextField(name='value'),
        models.DateTimeField(name='expires', db_index=True),
    )
    table_output = []
    index_output = []
    for f in fields:
        field_output = [backend.quote_name(f.name), data_types[f.get_internal_type()] % f.__dict__]
        field_output.append("%sNULL" % (not f.null and "NOT " or ""))
        if f.unique:
            field_output.append("UNIQUE")
        if f.primary_key:
            field_output.append("PRIMARY KEY")
        if f.db_index:
            unique = f.unique and "UNIQUE " or ""
            index_output.append("CREATE %sINDEX %s_%s ON %s (%s);" % \
                (unique, tablename, f.name, backend.quote_name(tablename),
                backend.quote_name(f.name)))
        table_output.append(" ".join(field_output))
    full_statement = ["CREATE TABLE %s (" % backend.quote_name(tablename)]
    for i, line in enumerate(table_output):
        full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
    full_statement.append(');')
    curs = connection.cursor()
    curs.execute("\n".join(full_statement))
    for statement in index_output:
        curs.execute(statement)
    transaction.commit_unless_managed()
createcachetable.args = "[tablename]"

def run_shell(use_plain=False):
    "Runs a Python interactive interpreter. Tries to use IPython, if it's available."
    try:
        if use_plain:
            # Don't bother loading IPython, because the user wants plain Python.
            raise ImportError
        import IPython
        # Explicitly pass an empty list as arguments, because otherwise IPython
        # would use sys.argv from this script.
        shell = IPython.Shell.IPShell(argv=[])
        shell.mainloop()
    except ImportError:
        import code
        try: # Try activating rlcompleter, because it's handy.
            import readline
        except ImportError:
            pass
        else:
            # We don't have to wrap the following import in a 'try', because
            # we already know 'readline' was imported successfully.
            import rlcompleter
            readline.parse_and_bind("tab:complete")
        code.interact()
run_shell.args = '[--plain]'

def dbshell():
    "Runs the command-line client for the current DATABASE_ENGINE."
    from django.db import runshell
    runshell()
dbshell.args = ""

def runfcgi(args):
    """Run this project as a FastCGI application. requires flup."""
    from django.core.servers.fastcgi import runfastcgi
    runfastcgi(args)
runfcgi.args = '[various KEY=val options, use `runfcgi help` for help]'

# Utilities for command-line script

DEFAULT_ACTION_MAPPING = {
    'adminindex': get_admin_index,
    'createcachetable' : createcachetable,
    'dbshell': dbshell,
    'diffsettings': diffsettings,
    'inspectdb': inspectdb,
    'install': install,
    'reset': reset,
    'runfcgi': runfcgi,
    'runserver': runserver,
    'shell': run_shell,
    'sql': get_sql_create,
    'sqlall': get_sql_all,
    'sqlclear': get_sql_delete,
    'sqlindexes': get_sql_indexes,
    'sqlinitialdata': get_sql_initial_data,
    'sqlreset': get_sql_reset,
    'sqlsequencereset': get_sql_sequence_reset,
    'startapp': startapp,
    'startproject': startproject,
    'syncdb': syncdb,
    'validate': validate,
}

NO_SQL_TRANSACTION = (
    'adminindex',
    'createcachetable',
    'dbshell',
    'diffsettings',
    'install',
    'reset',
    'sqlindexes',
    'syncdb',
)

class DjangoOptionParser(OptionParser):
    def print_usage_and_exit(self):
        self.print_help(sys.stderr)
        sys.exit(1)

def get_usage(action_mapping):
    """
    Returns a usage string. Doesn't do the options stuff, because optparse
    takes care of that.
    """
    usage = ["%prog action [options]\nactions:"]
    available_actions = action_mapping.keys()
    available_actions.sort()
    for a in available_actions:
        func = action_mapping[a]
        usage.append("  %s %s" % (a, func.args))
        usage.extend(textwrap.wrap(getattr(func, 'help_doc', textwrap.dedent(func.__doc__.strip())), initial_indent='    ', subsequent_indent='    '))
        usage.append("")
    return '\n'.join(usage[:-1]) # Cut off last list element, an empty space.

def print_error(msg, cmd):
    sys.stderr.write(style.ERROR('Error: %s' % msg) + '\nRun "%s --help" for help.\n' % cmd)
    sys.exit(1)

def execute_from_command_line(action_mapping=DEFAULT_ACTION_MAPPING, argv=None):
    # Use sys.argv if we've not passed in a custom argv
    if argv is None:
        argv = sys.argv

    # Parse the command-line arguments. optparse handles the dirty work.
    parser = DjangoOptionParser(usage=get_usage(action_mapping), version=get_version())
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings.main". If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be used.')
    parser.add_option('--pythonpath',
        help='Lets you manually add a directory the Python path, e.g. "/home/djangoprojects/myproject".')
    parser.add_option('--plain', action='store_true', dest='plain',
        help='Tells Django to use plain Python, not IPython, for "shell" command.')
    parser.add_option('--noreload', action='store_false', dest='use_reloader', default=True,
        help='Tells Django to NOT use the auto-reloader when running the development server.')
    options, args = parser.parse_args(argv[1:])

    # Take care of options.
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)

    # Run the appropriate action. Unfortunately, optparse can't handle
    # positional arguments, so this has to parse/validate them.
    try:
        action = args[0]
    except IndexError:
        parser.print_usage_and_exit()
    if not action_mapping.has_key(action):
        print_error("Your action, %r, was invalid." % action, argv[0])

    # Switch to English, because django-admin.py creates database content
    # like permissions, and those shouldn't contain any translations.
    # But only do this if we should have a working settings file.
    if action not in ('startproject', 'startapp'):
        from django.utils import translation
        translation.activate('en-us')

    if action == 'shell':
        action_mapping[action](options.plain is True)
    elif action in ('syncdb', 'validate', 'diffsettings', 'dbshell'):
        action_mapping[action]()
    elif action == 'inspectdb':
        try:
            for line in action_mapping[action]():
                print line
        except NotImplementedError:
            sys.stderr.write(style.ERROR("Error: %r isn't supported for the currently selected database backend.\n" % action))
            sys.exit(1)
    elif action == 'createcachetable':
        try:
            action_mapping[action](args[1])
        except IndexError:
            parser.print_usage_and_exit()
    elif action in ('startapp', 'startproject'):
        try:
            name = args[1]
        except IndexError:
            parser.print_usage_and_exit()
        action_mapping[action](name, os.getcwd())
    elif action == 'runserver':
        if len(args) < 2:
            addr = ''
            port = '8000'
        else:
            try:
                addr, port = args[1].split(':')
            except ValueError:
                addr, port = '', args[1]
        action_mapping[action](addr, port, options.use_reloader)
    elif action == 'runfcgi':
        action_mapping[action](args[1:])
    else:
        from django.db import models
        try:
            mod_list = [models.get_app(app_label) for app_label in args[1:]]
        except ImportError, e:
            sys.stderr.write(style.ERROR("Error: %s. Are you sure your INSTALLED_APPS setting is correct?\n" % e))
            sys.exit(1)
        if not mod_list:
            parser.print_usage_and_exit()
        if action not in NO_SQL_TRANSACTION:
            print style.SQL_KEYWORD("BEGIN;")
        for mod in mod_list:
            output = action_mapping[action](mod)
            if output:
                print '\n'.join(output)
        if action not in NO_SQL_TRANSACTION:
            print style.SQL_KEYWORD("COMMIT;")

def execute_manager(settings_mod, argv=None):
    # Add this project to sys.path so that it's importable in the conventional
    # way. For example, if this file (manage.py) lives in a directory
    # "myproject", this code would add "/path/to/myproject" to sys.path.
    project_directory = os.path.dirname(settings_mod.__file__)
    project_name = os.path.basename(project_directory)
    sys.path.append(os.path.join(project_directory, '..'))
    project_module = __import__(project_name, '', '', [''])
    sys.path.pop()

    # Set DJANGO_SETTINGS_MODULE appropriately.
    os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings' % project_name

    action_mapping = DEFAULT_ACTION_MAPPING.copy()

    # Remove the "startproject" command from the action_mapping, because that's
    # a django-admin.py command, not a manage.py command.
    del action_mapping['startproject']

    # Override the startapp handler so that it always uses the
    # project_directory, not the current working directory (which is default).
    action_mapping['startapp'] = lambda app_name, directory: startapp(app_name, project_directory)
    action_mapping['startapp'].__doc__ = startapp.__doc__
    action_mapping['startapp'].help_doc = startapp.help_doc
    action_mapping['startapp'].args = startapp.args

    # Run the django-admin.py command.
    execute_from_command_line(action_mapping, argv)
