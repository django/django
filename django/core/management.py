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
        v += '-' + VERSION[-1]
    return v

def get_sql_create(app):
    "Returns a list of the CREATE TABLE SQL statements for the given app."
    from django.db import models, model_connection_name

    # final output will be divided by comments into sections for each
    # named connection, if there are any named connections
    connection_output = {}
    pending = {}
    final_output = []
    
    app_models = models.get_models(app, creation_order=True)
    for model in app_models:
        opts = model._meta
        connection_name = model_connection_name(model)
        output = connection_output.setdefault(connection_name, [])
        db = model._default_manager.db
        creation = db.get_creation_module()
        data_types = creation.DATA_TYPES
        if not data_types:
            # This must be the "dummy" database backend, which means the user
            # hasn't set DATABASE_ENGINE.

            # FIXME diff error message for bad default v bad named
            sys.stderr.write(style.ERROR("Error: Django doesn't know which syntax to use for your SQL statements,\n" +
                                         "because you haven't specified the DATABASE_ENGINE setting.\n" +
                                         "Edit your settings file and change DATABASE_ENGINE to something like 'postgresql' or 'mysql'.\n"))
            sys.exit(1)

        # Get installed models, so we generate REFERENCES right
        # We trim models from the current app so that the sqlreset command does
        # not generate invalid SQL (leaving models out of known_models is 
        # harmless, so we can be conservative).
        manager = model._default_manager
        try:
            tables = manager.get_table_list()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # Something else went wrong -- maybe the database isn't
            # running. But we can still generate sql, so use an empty
            # table list.
            tables = []

        installed_models = [ m for m in
                             manager.get_installed_models(tables)
                             if m not in app_models ]
        models_output = set(installed_models) 
        builder = creation.builder
        builder.models_already_seen.update(models_output)
        model_output, pending = builder.get_create_table(model, style, pending)
        output.extend(model_output)

        # Create the many-to-many join tables.
        many_many = builder.get_create_many_to_many(model, style)
        for refmodel, statements in many_many.items():
            output.extend(statements)

    final_output = _collate(connection_output)
    
    # Handle references to tables that are from other apps
    # but don't exist physically
    not_installed_models = set(pending.keys())
    if not_installed_models:
        alter_sql = []
        for model in not_installed_models:
            builder = model._default_manager.db.get_creation_module().builder
            
            for rel_class, f in pending[model]:
                sql = builder.get_ref_sql(model, rel_class, f, style)
                alter_sql.append('-- '+ str(sql))
        if alter_sql:
            final_output.append('-- The following references should be added '
                                'but depend on non-existent tables:')
            final_output.extend(alter_sql)
    # convert BoundStatements into strings
    final_output = map(str, final_output)
    return final_output
get_sql_create.help_doc = "Prints the CREATE TABLE SQL statements for the given app name(s)."
get_sql_create.args = APP_ARGS


def get_sql_delete(app):
    "Returns a list of the DROP TABLE SQL statements for the given app."
    from django.db import models, model_connection_name
    
    connection_output = {}
    final_output = []
    app_models = models.get_models(app, creation_order=True)
    for model in app_models:
        db = model._default_manager.db
        connection = db.connection
        try:
            cursor = connection.cursor()
        except:
            cursor = None
        builder = db.get_creation_module().builder
        connection_name = model_connection_name(model)
        output = connection_output.setdefault(connection_name, [])
        output.extend(map(str,
                          builder.get_drop_table(model,
                                                 cascade=True, style=style)))
        if cursor:
            # Close database connection explicitly, in case this
            # output is being piped directly into a database client,
            # to avoid locking issues.
            cursor.close()
            connection.close()
    # Reverse it, to deal with table dependencies.
    final_output = _collate(connection_output, reverse=True)
    return final_output
get_sql_delete.help_doc = "Prints the DROP TABLE SQL statements for the given app name(s)."
get_sql_delete.args = APP_ARGS

def get_sql_reset(app):
    "Returns a list of the DROP TABLE SQL, then the CREATE TABLE SQL, for the given module."
    return get_sql_delete(app) + get_sql_all(app)
get_sql_reset.help_doc = "Prints the DROP TABLE SQL, then the CREATE TABLE SQL, for the given app name(s)."
get_sql_reset.args = APP_ARGS

def get_sql_initial_data(app):
    "Returns a list of the initial INSERT SQL statements for the given app."
    from django.db import model_connection_name
    from django.db.models import get_models
    connection_output = {}

    app_models = get_models(app)
    for model in app_models:
        opts = model._meta
        connection_name = model_connection_name(model)
        output = connection_output.setdefault(connection_name, [])
        builder = model._default_manager.db.get_creation_module().builder
        output.extend(builder.get_initialdata(model))

    return _collate(connection_output)
get_sql_initial_data.help_doc = "Prints the initial INSERT SQL statements for the given app name(s)."
get_sql_initial_data.args = APP_ARGS

def get_sql_sequence_reset(app):
    "Returns a list of the SQL statements to reset PostgreSQL sequences for the given app."
    from django.db import model_connection_name
    from django.db.models import get_models
    connection_output = {}
    for model in get_models(app):
        connection_name = model_connection_name(model)
        output = connection_output.setdefault(connection_name, [])
        builder = model._default_manager.db.get_creation_module().builder
        try:
            output.extend(builder.get_sequence_reset(model, style))
        except AttributeError:
            sys.stderr.write(
                "%s is configured to use database engine %s, which does " 
                "not support sequence reset.\n" % 
                (model.__name__,
                 model._default_manager.db.connection.settings.DATABASE_ENGINE))
    
    return _collate(connection_output)
get_sql_sequence_reset.help_doc = "Prints the SQL statements for resetting PostgreSQL sequences for the given app name(s)."
get_sql_sequence_reset.args = APP_ARGS

def get_sql_indexes(app):
    "Returns a list of the CREATE INDEX SQL statements for the given app."
    from django.db import model_connection_name
    from django.db.models import get_models
    connection_output = {}

    for model in get_models(app):
        opts = model._meta
        connection_name = model_connection_name(model)
        output = connection_output.setdefault(connection_name, [])
        builder = model._default_manager.db.get_creation_module().builder
        output.extend(map(str, builder.get_create_indexes(model, style)))
    return _collate(connection_output)

get_sql_indexes.help_doc = "Prints the CREATE INDEX SQL statements for the given model module name(s)."
get_sql_indexes.args = APP_ARGS

def get_sql_all(app):
    "Returns a list of CREATE TABLE SQL, initial-data inserts, and CREATE INDEX SQL for the given module."
    return get_sql_create(app) + get_sql_initial_data(app) + get_sql_indexes(app)
get_sql_all.help_doc = "Prints the CREATE TABLE, initial-data and CREATE INDEX SQL statements for the given model module name(s)."
get_sql_all.args = APP_ARGS

def _collate(connection_output, reverse=False):
    from django.db import _default
    final_output = []
    if len(connection_output.keys()) == 1:
        # all for the default connection
        for statements in connection_output.values():
            final_output.extend(statements)
            if reverse:
                final_output.reverse()
    else:
        for connection_name, statements in connection_output.items():
            if not statements:
                continue
            final_output.append(' -- The following statements are for connection: %s' % connection_name)
            if reverse:
                statements.reverse()
            final_output.extend(statements)
            final_output.append(' -- END statements for %s\n' %
                                connection_name)
    return map(str, final_output)

def syncdb(verbosity=2, interactive=True):
    "Creates the database tables for all apps in INSTALLED_APPS whose tables haven't already been created."
    from django.conf import settings
    from django.db import models, transaction
    from django.db.models import signals
    from django.dispatch import dispatcher
    
    disable_termcolors()

    # First, try validating the models.
    _check_for_validation_errors()

    # Create missing models for each app
    created_models = []
    for app_name in settings.INSTALLED_APPS:
        # Import the 'management' module within each installed app, to register
        # dispatcher events.
        try:
            __import__(app_name + '.management', '', '', [''])
        except ImportError:
            pass

    # Install each app
    pending = None
    for app in models.get_apps():
        # Install each application (models already installed will be skipped)
        created, pending = _install(app, commit=False, initial_data=False,
                                    pending_allowed=True, pending=pending)
        if verbosity >= 2:
            for model in created:
                print "Created table %s" % model._meta.db_table
        created_models.extend(created)
    if pending:
        transaction.rollback_unless_managed()
        raise Exception("All apps were installed, but there were still "
                        "pending references to: " + ",".join(pending.keys()) +
                        ". Transaction rolled back.")
    transaction.commit_unless_managed()

    # Send the post_syncdb signal, so individual apps can do whatever they need
    # to do at this point.
    for app in models.get_apps():
        dispatcher.send(signal=signals.post_syncdb, sender=app,
            app=app, created_models=created_models,
            verbosity=verbosity, interactive=interactive)

    # Install initial data for the app (but only if this is a model we've
    # just created)
    for app in models.get_apps():
        for model in models.get_models(app):
            if model in created_models:
                try:
                    if (model._default_manager.load_initial_data() 
                        and verbosity >= 2):
                        print "Installed initial data for %s model" % model._meta.object_name
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

    user_settings = _module_to_dict(settings._target)
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
    # Wrap _install to hide the return value so ./manage.py install
    # doesn't complain about unprintable output.    
    _install(app)

def _install(app, commit=True, initial_data=True, pending_allowed=False,
             pending=None):
    from django.db import connection, models, transaction
    import sys
    
    app_name = app.__name__.split('.')[-2]

    disable_termcolors()

    # First, try validating the models.
    _check_for_validation_errors(app)

    created_models = []
    try:
        if pending is None:
            pending = {}
        for model in models.get_models(app, creation_order=True):
            manager = model._default_manager
            tables = manager.get_table_list()
            models_installed = manager.get_installed_models(tables)
            # Don't re-install already-installed models
            if not model in models_installed:
                pending = manager.install(initial_data=initial_data,
                                          pending=pending)
                created_models.append(model)
                
        if pending:            
            models_installed = manager.get_installed_models(tables)

            for model in pending.keys():
                manager = model._default_manager
                if model in models_installed:
                    for rel_class, f in pending[model]:
                        manager.get_pending(rel_class, f).execute()
                    pending.pop(model)
                elif not pending_allowed:
                    raise Exception("%s is not installed, but it has pending "
                                    "references" % model)
    except Exception, e:
        import traceback
        print traceback.format_exception(*sys.exc_info())
        sys.stderr.write(style.ERROR("""Error: %s couldn't be installed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the database tables already exists.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlall %s'. That's the SQL this command wasn't able to run.
The full error: """ % (app_name, app_name)) + style.ERROR_OUTPUT(str(e)) + '\n')
        transaction.rollback_unless_managed()
        sys.exit(1)
    if commit:
        transaction.commit_unless_managed()
    return created_models, pending
install.help_doc = "Executes ``sqlall`` for the given app(s) in the current database."
install.args = APP_ARGS

def reset(app):
    "Executes the equivalent of 'get_sql_reset' in the current database."
    from django.db import connection, transaction
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
    import keyword

    introspection_module = get_introspection_module()

    table2model = lambda table_name: table_name.title().replace('_', '')

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

            if ' ' in att_name:
                extra_params['db_column'] = att_name
                att_name = att_name.replace(' ', '')
                comment_notes.append('Field renamed to remove spaces.')
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
    from django.db import models, model_connection_name
    from django.db.models.loading import get_app_errors
    from django.db.models.fields.related import RelatedObject

    e = ModelErrorCollection(outfile)

    for (app_name, error) in get_app_errors().items():
        e.add(app_name, error)

    for cls in models.get_models(app):
        opts = cls._meta
        connection_name = model_connection_name(cls)
        
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

                rel_connection = model_connection_name(f.rel.to)
                if rel_connection != connection_name:
                    e.add(opts, "'%s' is configured to use connection '%s' but has relation with '%s', which is configured to use connection '%s'" % (cls.__name__, connection_name, f.rel.to.__name__, rel_connection))

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
            # If rel_name is none, there is no reverse accessor.
            # (This only occurs for symmetrical m2m relations to self).
            # If this is the case, there are no clashes to check for this field, as
            # there are no reverse descriptors for this field.
            if rel_name is not None:
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
                # date_hierarchy
                if opts.admin.date_hierarchy:
                    try:
                        f = opts.get_field(opts.admin.date_hierarchy)
                    except models.FieldDoesNotExist:
                        e.add(opts, '"admin.date_hierarchy" refers to %r, which isn\'t a field.' % opts.admin.date_hierarchy)

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
    "Runs this project as a FastCGI application. Requires flup."
    from django.conf import settings
    from django.utils import translation
    # Activate the current language, because it won't get activated later.
    try:
        translation.activate(settings.LANGUAGE_CODE)
    except AttributeError:
        pass
    from django.core.servers.fastcgi import runfastcgi
    runfastcgi(args)
runfcgi.args = '[various KEY=val options, use `runfcgi help` for help]'

def test(verbosity, app_labels):
    "Runs the test suite for the specified applications"
    from django.conf import settings
    from django.db.models import get_app, get_apps

    if len(app_labels) == 0:
        app_list = get_apps()
    else:
        app_list = [get_app(app_label) for app_label in app_labels]

    test_path = settings.TEST_RUNNER.split('.')
    # Allow for Python 2.5 relative paths
    if len(test_path) > 1:
        test_module_name = '.'.join(test_path[:-1])
    else:
        test_module_name = '.'
    test_module = __import__(test_module_name, [],[],test_path[-1])
    test_runner = getattr(test_module, test_path[-1])

    test_runner(app_list, verbosity)
test.help_doc = 'Runs the test suite for the specified applications, or the entire site if no apps are specified'
test.args = '[--verbosity] ' + APP_ARGS

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
    'test':test,
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
    parser.add_option('--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option('--noreload', action='store_false', dest='use_reloader', default=True,
        help='Tells Django to NOT use the auto-reloader when running the development server.')
    parser.add_option('--verbosity', action='store', dest='verbosity', default='2',
        type='choice', choices=['0', '1', '2'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all output')

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
    elif action in ('validate', 'diffsettings', 'dbshell'):
        action_mapping[action]()
    elif action == 'syncdb':
        action_mapping[action](int(options.verbosity), options.interactive)
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
    elif action == 'test':
        try:
            action_mapping[action](int(options.verbosity), args[1:])
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

def setup_environ(settings_mod):
    """
    Configure the runtime environment. This can also be used by external
    scripts wanting to set up a similar environment to manage.py.
    """
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
    return project_directory

def execute_manager(settings_mod, argv=None):
    project_directory = setup_environ(settings_mod)
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
