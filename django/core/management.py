# Django management-related functions, including "CREATE TABLE" generation and
# development-server initialization.

import django
import os, re, sys

MODULE_TEMPLATE = '''    {%% if perms.%(app)s.%(addperm)s or perms.%(app)s.%(changeperm)s %%}
    <tr>
        <th>{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/">{%% endif %%}%(name)s{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</th>
        <td class="x50">{%% if perms.%(app)s.%(addperm)s %%}<a href="%(app)s/%(mod)s/add/" class="addlink">{%% endif %%}Add{%% if perms.%(app)s.%(addperm)s %%}</a>{%% endif %%}</td>
        <td class="x75">{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/" class="changelink">{%% endif %%}Change{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</td>
    </tr>
    {%% endif %%}'''

APP_ARGS = '[modelmodule ...]'

# Use django.__path__[0] because we don't know which directory django into
# which has been installed.
PROJECT_TEMPLATE_DIR = os.path.join(django.__path__[0], 'conf', '%s_template')

def _get_packages_insert(app_label):
    from django.core.db import db
    return "INSERT INTO %s (%s, %s) VALUES ('%s', '%s');" % \
        (db.quote_name('packages'), db.quote_name('label'), db.quote_name('name'),
        app_label, app_label)

def _get_permission_codename(action, opts):
    return '%s_%s' % (action, opts.object_name.lower())

def _get_all_permissions(opts):
    "Returns (codename, name) for all permissions in the given opts."
    perms = []
    if opts.admin:
        for action in ('add', 'change', 'delete'):
            perms.append((_get_permission_codename(action, opts), 'Can %s %s' % (action, opts.verbose_name)))
    return perms + list(opts.permissions)

def _get_permission_insert(name, codename, opts):
    from django.core.db import db
    return "INSERT INTO %s (%s, %s, %s) VALUES ('%s', '%s', '%s');" % \
        (db.quote_name('auth_permissions'), db.quote_name('name'), db.quote_name('package'),
        db.quote_name('codename'), name.replace("'", "''"), opts.app_label, codename)

def _get_contenttype_insert(opts):
    from django.core.db import db
    return "INSERT INTO %s (%s, %s, %s) VALUES ('%s', '%s', '%s');" % \
        (db.quote_name('content_types'), db.quote_name('name'), db.quote_name('package'),
        db.quote_name('python_module_name'), opts.verbose_name, opts.app_label, opts.module_name)

def _is_valid_dir_name(s):
    return bool(re.search(r'^\w+$', s))

# If the foreign key points to an AutoField, the foreign key should be an
# IntegerField, not an AutoField. Otherwise, the foreign key should be the same
# type of field as the field to which it points.
get_rel_data_type = lambda f: (f.get_internal_type() == 'AutoField') and 'IntegerField' or f.get_internal_type()

def get_sql_create(mod):
    "Returns a list of the CREATE TABLE SQL statements for the given module."
    from django.core import db, meta
    final_output = []
    for klass in mod._MODELS:
        opts = klass._meta
        table_output = []
        for f in opts.fields:
            if isinstance(f, meta.ForeignKey):
                rel_field = f.rel.get_related_field()
                data_type = get_rel_data_type(rel_field)
            else:
                rel_field = f
                data_type = f.get_internal_type()
            col_type = db.DATA_TYPES[data_type]
            if col_type is not None:
                field_output = [db.db.quote_name(f.column), col_type % rel_field.__dict__]
                field_output.append('%sNULL' % (not f.null and 'NOT ' or ''))
                if f.unique:
                    field_output.append('UNIQUE')
                if f.primary_key:
                    field_output.append('PRIMARY KEY')
                if f.rel:
                    field_output.append('REFERENCES %s (%s)' % \
                        (db.db.quote_name(f.rel.to.db_table),
                        db.db.quote_name(f.rel.to.get_field(f.rel.field_name).column)))
                table_output.append(' '.join(field_output))
        if opts.order_with_respect_to:
            table_output.append('%s %s NULL' % (db.db.quote_name('_order'), db.DATA_TYPES['IntegerField']))
        for field_constraints in opts.unique_together:
            table_output.append('UNIQUE (%s)' % \
                ", ".join([db.db.quote_name(opts.get_field(f).column) for f in field_constraints]))

        full_statement = ['CREATE TABLE %s (' % db.db.quote_name(opts.db_table)]
        for i, line in enumerate(table_output): # Combine and add commas.
            full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
        full_statement.append(');')
        final_output.append('\n'.join(full_statement))

    for klass in mod._MODELS:
        opts = klass._meta
        for f in opts.many_to_many:
            table_output = ['CREATE TABLE %s (' % db.db.quote_name(f.get_m2m_db_table(opts))]
            table_output.append('    %s %s NOT NULL PRIMARY KEY,' % (db.db.quote_name('id'), db.DATA_TYPES['AutoField']))
            table_output.append('    %s %s NOT NULL REFERENCES %s (%s),' % \
                (db.db.quote_name(opts.object_name.lower() + '_id'),
                db.DATA_TYPES[get_rel_data_type(opts.pk)] % opts.pk.__dict__,
                db.db.quote_name(opts.db_table),
                db.db.quote_name(opts.pk.column)))
            table_output.append('    %s %s NOT NULL REFERENCES %s (%s),' % \
                (db.db.quote_name(f.rel.to.object_name.lower() + '_id'),
                db.DATA_TYPES[get_rel_data_type(f.rel.to.pk)] % f.rel.to.pk.__dict__,
                db.db.quote_name(f.rel.to.db_table),
                db.db.quote_name(f.rel.to.pk.column)))
            table_output.append('    UNIQUE (%s, %s)' % \
                (db.db.quote_name(opts.object_name.lower() + '_id'),
                db.db.quote_name(f.rel.to.object_name.lower() + '_id')))
            table_output.append(');')
            final_output.append('\n'.join(table_output))
    return final_output
get_sql_create.help_doc = "Prints the CREATE TABLE SQL statements for the given model module name(s)."
get_sql_create.args = APP_ARGS

def get_sql_delete(mod):
    "Returns a list of the DROP TABLE SQL statements for the given module."
    from django.core import db
    try:
        cursor = db.db.cursor()
    except:
        cursor = None

    # Determine whether the admin log table exists. It only exists if the
    # person has installed the admin app.
    try:
        if cursor is not None:
            # Check whether the table exists.
            cursor.execute("SELECT 1 FROM %s LIMIT 1" % db.db.quote_name('django_admin_log'))
    except:
        # The table doesn't exist, so it doesn't need to be dropped.
        db.db.rollback()
        admin_log_exists = False
    else:
        admin_log_exists = True

    output = []

    # Output DROP TABLE statements for standard application tables.
    for klass in mod._MODELS:
        try:
            if cursor is not None:
                # Check whether the table exists.
                cursor.execute("SELECT 1 FROM %s LIMIT 1" % db.db.quote_name(klass._meta.db_table))
        except:
            # The table doesn't exist, so it doesn't need to be dropped.
            db.db.rollback()
        else:
            output.append("DROP TABLE %s;" % db.db.quote_name(klass._meta.db_table))

    # Output DROP TABLE statements for many-to-many tables.
    for klass in mod._MODELS:
        opts = klass._meta
        for f in opts.many_to_many:
            try:
                if cursor is not None:
                    cursor.execute("SELECT 1 FROM %s LIMIT 1" % db.db.quote_name(f.get_m2m_db_table(opts)))
            except:
                db.db.rollback()
            else:
                output.append("DROP TABLE %s;" % db.db.quote_name(f.get_m2m_db_table(opts)))

    app_label = mod._MODELS[0]._meta.app_label

    # Delete from packages, auth_permissions, content_types.
    output.append("DELETE FROM %s WHERE %s = '%s';" % \
        (db.db.quote_name('packages'), db.db.quote_name('label'), app_label))
    output.append("DELETE FROM %s WHERE %s = '%s';" % \
        (db.db.quote_name('auth_permissions'), db.db.quote_name('package'), app_label))
    output.append("DELETE FROM %s WHERE %s = '%s';" % \
        (db.db.quote_name('content_types'), db.db.quote_name('package'), app_label))

    # Delete from the admin log.
    if cursor is not None:
        cursor.execute("SELECT %s FROM %s WHERE %s = %%s" % \
            (db.db.quote_name('id'), db.db.quote_name('content_types'),
            db.db.quote_name('package')), [app_label])
        if admin_log_exists:
            for row in cursor.fetchall():
                output.append("DELETE FROM %s WHERE %s = %s;" % \
                    (db.db.quote_name('django_admin_log'), db.db.quote_name('content_type_id'), row[0]))

    # Close database connection explicitly, in case this output is being piped
    # directly into a database client, to avoid locking issues.
    cursor.close()
    db.db.close()

    return output[::-1] # Reverse it, to deal with table dependencies.
get_sql_delete.help_doc = "Prints the DROP TABLE SQL statements for the given model module name(s)."
get_sql_delete.args = APP_ARGS

def get_sql_reset(mod):
    "Returns a list of the DROP TABLE SQL, then the CREATE TABLE SQL, for the given module."
    return get_sql_delete(mod) + get_sql_all(mod)
get_sql_reset.help_doc = "Prints the DROP TABLE SQL, then the CREATE TABLE SQL, for the given model module name(s)."
get_sql_reset.args = APP_ARGS

def get_sql_initial_data(mod):
    "Returns a list of the initial INSERT SQL statements for the given module."
    from django.core import db
    output = []
    app_label = mod._MODELS[0]._meta.app_label
    output.append(_get_packages_insert(app_label))
    app_dir = os.path.normpath(os.path.join(os.path.dirname(mod.__file__), '..', 'sql'))
    for klass in mod._MODELS:
        opts = klass._meta

        # Add custom SQL, if it's available.
        sql_files = [os.path.join(app_dir, opts.module_name + '.' + db.DATABASE_ENGINE +  '.sql'),
                     os.path.join(app_dir, opts.module_name + '.sql')]
        for sql_file in sql_files:
            if os.path.exists(sql_file):
                fp = open(sql_file)
                output.append(fp.read())
                fp.close()

        # Content types.
        output.append(_get_contenttype_insert(opts))
        # Permissions.
        for codename, name in _get_all_permissions(opts):
            output.append(_get_permission_insert(name, codename, opts))
    return output
get_sql_initial_data.help_doc = "Prints the initial INSERT SQL statements for the given model module name(s)."
get_sql_initial_data.args = APP_ARGS

def get_sql_sequence_reset(mod):
    "Returns a list of the SQL statements to reset PostgreSQL sequences for the given module."
    from django.core import db, meta
    output = []
    for klass in mod._MODELS:
        for f in klass._meta.fields:
            if isinstance(f, meta.AutoField):
                output.append("SELECT setval('%s_%s_seq', (SELECT max(%s) FROM %s));" % \
                    (klass._meta.db_table, f.column, db.db.quote_name(f.column),
                    db.db.quote_name(klass._meta.db_table)))
        for f in klass._meta.many_to_many:
            output.append("SELECT setval('%s_id_seq', (SELECT max(%s) FROM %s));" % \
                (f.get_m2m_db_table(klass._meta), db.db.quote_name('id'), f.get_m2m_db_table(klass._meta)))
    return output
get_sql_sequence_reset.help_doc = "Prints the SQL statements for resetting PostgreSQL sequences for the given model module name(s)."
get_sql_sequence_reset.args = APP_ARGS

def get_sql_indexes(mod):
    "Returns a list of the CREATE INDEX SQL statements for the given module."
    from django.core.db import db
    output = []
    for klass in mod._MODELS:
        for f in klass._meta.fields:
            if f.db_index:
                unique = f.unique and "UNIQUE " or ""
                output.append("CREATE %sINDEX %s_%s ON %s (%s);" % \
                    (unique, klass._meta.db_table, f.column,
                    db.quote_name(klass._meta.db_table), db.quote_name(f.column)))
    return output
get_sql_indexes.help_doc = "Prints the CREATE INDEX SQL statements for the given model module name(s)."
get_sql_indexes.args = APP_ARGS

def get_sql_all(mod):
    "Returns a list of CREATE TABLE SQL and initial-data insert for the given module."
    return get_sql_create(mod) + get_sql_initial_data(mod)
get_sql_all.help_doc = "Prints the CREATE TABLE and initial-data SQL statements for the given model module name(s)."
get_sql_all.args = APP_ARGS

def has_no_records(cursor):
    "Returns True if the cursor, having executed a query, returned no records."
    # This is necessary due to an inconsistency in the DB-API spec.
    # cursor.rowcount can be -1 (undetermined), according to
    # http://www.python.org/peps/pep-0249.html
    if cursor.rowcount < 0:
        return cursor.fetchone() is None
    return cursor.rowcount < 1

def database_check(mod):
    "Checks that everything is properly installed in the database for the given module."
    from django.core import db
    cursor = db.db.cursor()
    app_label = mod._MODELS[0]._meta.app_label

    # Check that the package exists in the database.
    cursor.execute("SELECT 1 FROM %s WHERE %s = %%s" % \
        (db.db.quote_name('packages'), db.db.quote_name('label')), [app_label])
    if has_no_records(cursor):
#         sys.stderr.write("The '%s' package isn't installed.\n" % app_label)
        print _get_packages_insert(app_label)

    # Check that the permissions and content types are in the database.
    perms_seen = {}
    contenttypes_seen = {}
    for klass in mod._MODELS:
        opts = klass._meta
        perms = _get_all_permissions(opts)
        perms_seen.update(dict(perms))
        contenttypes_seen[opts.module_name] = 1
        for codename, name in perms:
            cursor.execute("SELECT 1 FROM %s WHERE %s = %%s AND %s = %%s" % \
                (db.db.quote_name('auth_permissions'), db.db.quote_name('package'),
                db.db.quote_name('codename')), (app_label, codename))
            if has_no_records(cursor):
#                 sys.stderr.write("The '%s.%s' permission doesn't exist.\n" % (app_label, codename))
                print _get_permission_insert(name, codename, opts)
        cursor.execute("SELECT 1 FROM %s WHERE %s = %%s AND %s = %%s" % \
            (db.db.quote_name('content_types'), db.db.quote_name('package'),
            db.db.quote_name('python_module_name')), (app_label, opts.module_name))
        if has_no_records(cursor):
#             sys.stderr.write("The '%s.%s' content type doesn't exist.\n" % (app_label, opts.module_name))
            print _get_contenttype_insert(opts)

    # Check that there aren't any *extra* permissions in the DB that the model
    # doesn't know about.
    cursor.execute("SELECT %s FROM %s WHERE %s = %%s" % \
        (db.db.quote_name('codename'), db.db.quote_name('auth_permissions'),
        db.db.quote_name('package')), (app_label,))
    for row in cursor.fetchall():
        try:
            perms_seen[row[0]]
        except KeyError:
#             sys.stderr.write("A permission called '%s.%s' was found in the database but not in the model.\n" % (app_label, row[0]))
            print "DELETE FROM %s WHERE %s='%s' AND %s = '%s';" % \
                (db.db.quote_name('auth_permissions'), db.db.quote_name('package'),
                app_label, db.db.quote_name('codename'), row[0])

    # Check that there aren't any *extra* content types in the DB that the
    # model doesn't know about.
    cursor.execute("SELECT %s FROM %s WHERE %s = %%s" % \
        (db.db.quote_name('python_module_name'), db.db.quote_name('content_types'),
        db.db.quote_name('package')), (app_label,))
    for row in cursor.fetchall():
        try:
            contenttypes_seen[row[0]]
        except KeyError:
#             sys.stderr.write("A content type called '%s.%s' was found in the database but not in the model.\n" % (app_label, row[0]))
            print "DELETE FROM %s WHERE %s='%s' AND %s = '%s';" % \
                (db.db.quote_name('content_types'), db.db.quote_name('package'),
                app_label, db.db.quote_name('python_module_name'), row[0])
database_check.help_doc = "Checks that everything is installed in the database for the given model module name(s) and prints SQL statements if needed."
database_check.args = APP_ARGS

def get_admin_index(mod):
    "Returns admin-index template snippet (in list form) for the given module."
    from django.utils.text import capfirst
    output = []
    app_label = mod._MODELS[0]._meta.app_label
    output.append('{%% if perms.%s %%}' % app_label)
    output.append('<div class="module"><h2>%s</h2><table>' % app_label.title())
    for klass in mod._MODELS:
        if klass._meta.admin:
            output.append(MODULE_TEMPLATE % {
                'app': app_label,
                'mod': klass._meta.module_name,
                'name': capfirst(klass._meta.verbose_name_plural),
                'addperm': klass._meta.get_add_permission(),
                'changeperm': klass._meta.get_change_permission(),
            })
    output.append('</table></div>')
    output.append('{% endif %}')
    return output
get_admin_index.help_doc = "Prints the admin-index template snippet for the given model module name(s)."
get_admin_index.args = APP_ARGS

def init():
    "Initializes the database with auth and core."
    try:
        from django.core import db, meta
        auth = meta.get_app('auth')
        core = meta.get_app('core')
        cursor = db.db.cursor()
        for sql in get_sql_create(core) + get_sql_create(auth) + get_sql_initial_data(core) + get_sql_initial_data(auth):
            cursor.execute(sql)
        cursor.execute("INSERT INTO %s (%s, %s) VALUES ('example.com', 'Example site')" % \
            (db.db.quote_name(core.Site._meta.db_table), db.db.quote_name('domain'),
            db.db.quote_name('name')))
    except Exception, e:
        sys.stderr.write("Error: The database couldn't be initialized.\n%s\n" % e)
        try:
            db.db.rollback()
        except UnboundLocalError:
            pass
        sys.exit(1)
    else:
        db.db.commit()
init.args = ''

def install(mod):
    "Executes the equivalent of 'get_sql_all' in the current database."
    from django.core import db
    from cStringIO import StringIO
    mod_name = mod.__name__[mod.__name__.rindex('.')+1:]

    # First, try validating the models.
    s = StringIO()
    num_errors = get_validation_errors(s)
    if num_errors:
        sys.stderr.write("Error: %s couldn't be installed, because there were errors in your model:\n" % mod_name)
        s.seek(0)
        sys.stderr.write(s.read())
        sys.exit(1)
    sql_list = get_sql_all(mod)

    try:
        cursor = db.db.cursor()
        for sql in sql_list:
            cursor.execute(sql)
    except Exception, e:
        sys.stderr.write("""Error: %s couldn't be installed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the database tables already exists.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlall %s'. That's the SQL this command wasn't able to run.
The full error: %s\n""" % \
            (mod_name, mod_name, e))
        db.db.rollback()
        sys.exit(1)
    db.db.commit()
install.help_doc = "Executes ``sqlall`` for the given model module name(s) in the current database."
install.args = APP_ARGS

def installperms(mod):
    "Installs any permissions for the given model, if needed."
    from django.models.auth import permissions
    from django.models.core import packages
    num_added = 0
    package = packages.get_object(pk=mod._MODELS[0]._meta.app_label)
    for klass in mod._MODELS:
        opts = klass._meta
        for codename, name in _get_all_permissions(opts):
            try:
                permissions.get_object(name__exact=name, codename__exact=codename, package__label__exact=package.label)
            except permissions.PermissionDoesNotExist:
                p = permissions.Permission(name=name, package=package, codename=codename)
                p.save()
                print "Added permission '%r'." % p
                num_added += 1
    if not num_added:
        print "No permissions were added, because all necessary permissions were already installed."
installperms.help_doc = "Installs any permissions for the given model module name(s), if needed."
installperms.args = APP_ARGS

def _start_helper(app_or_project, name, directory, other_name=''):
    other = {'project': 'app', 'app': 'project'}[app_or_project]
    if not _is_valid_dir_name(name):
        sys.stderr.write("Error: %r is not a valid %s name. Please use only numbers, letters and underscores.\n" % (name, app_or_project))
        sys.exit(1)
    top_dir = os.path.join(directory, name)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        sys.stderr.write("Error: %s\n" % e)
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
            fp_old = open(os.path.join(d, f), 'r')
            fp_new = open(os.path.join(top_dir, relative_dir, f.replace('%s_name' % app_or_project, name)), 'w')
            fp_new.write(fp_old.read().replace('{{ %s_name }}' % app_or_project, name).replace('{{ %s_name }}' % other, other_name))
            fp_old.close()
            fp_new.close()

def startproject(project_name, directory):
    "Creates a Django project for the given project_name in the given directory."
    from random import choice
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
    _start_helper('app', app_name, directory, project_name)
startapp.help_doc = "Creates a Django app directory structure for the given app name in the current directory."
startapp.args = "[appname]"

def createsuperuser(username=None, email=None, password=None):
    "Creates a superuser account."
    from django.core import validators
    from django.models.auth import users
    import getpass
    try:
        while 1:
            if not username:
                username = raw_input('Username (only letters, digits and underscores): ')
            if not username.isalnum():
                sys.stderr.write("Error: That username is invalid.\n")
                username = None
            try:
                users.get_object(username__exact=username)
            except users.UserDoesNotExist:
                break
            else:
                sys.stderr.write("Error: That username is already taken.\n")
                username = None
        while 1:
            if not email:
                email = raw_input('E-mail address: ')
            try:
                validators.isValidEmail(email, None)
            except validators.ValidationError:
                sys.stderr.write("Error: That e-mail address is invalid.\n")
                email = None
            else:
                break
        while 1:
            if not password:
                password = getpass.getpass()
                password2 = getpass.getpass('Password (again): ')
                if password != password2:
                    sys.stderr.write("Error: Your passwords didn't match.\n")
                    password = None
                    continue
            if password.strip() == '':
                sys.stderr.write("Error: Blank passwords aren't allowed.\n")
                password = None
                continue
            break
    except KeyboardInterrupt:
        sys.stderr.write("\nOperation cancelled.\n")
        sys.exit(1)
    u = users.create_user(username, email, password)
    u.is_staff = True
    u.is_active = True
    u.is_superuser = True
    u.save()
    print "User created successfully."
createsuperuser.args = '[username] [email] [password] (Either all or none)'

def inspectdb(db_name):
    "Generator that introspects the tables in the given database name and returns a Django model, one line at a time."
    from django.core import db
    from django.conf import settings

    def table2model(table_name):
        object_name = table_name.title().replace('_', '')
        return object_name.endswith('s') and object_name[:-1] or object_name

    settings.DATABASE_NAME = db_name
    cursor = db.db.cursor()
    yield "# This is an auto-generated Django model module."
    yield "# You'll have to do the following manually to clean this up:"
    yield "#     * Rearrange models' order"
    yield "#     * Add primary_key=True to one field in each model."
    yield "# Feel free to rename the models, but don't rename db_table values or field names."
    yield "#"
    yield "# Also note: You'll have to insert the output of 'django-admin.py sqlinitialdata [appname]'"
    yield "# into your database."
    yield ''
    yield 'from django.core import meta'
    yield ''
    for table_name in db.get_table_list(cursor):
        yield 'class %s(meta.Model):' % table2model(table_name)
        try:
            relations = db.get_relations(cursor, table_name)
        except NotImplementedError:
            relations = {}
        for i, row in enumerate(db.get_table_description(cursor, table_name)):
            column_name = row[0]
            if relations.has_key(i):
                rel = relations[i]
                rel_to = rel[1] == table_name and "'self'" or table2model(rel[1])
                if column_name.endswith('_id'):
                    field_desc = '%s = meta.ForeignKey(%s' % (column_name[:-3], rel_to)
                else:
                    field_desc = '%s = meta.ForeignKey(%s, db_column=%r' % (column_name, rel_to, column_name)
            else:
                try:
                    field_type = db.DATA_TYPES_REVERSE[row[1]]
                except KeyError:
                    field_type = 'TextField'
                    field_type_was_guessed = True
                else:
                    field_type_was_guessed = False
                field_desc = '%s = meta.%s(' % (column_name, field_type)
                if field_type == 'CharField':
                    field_desc += 'maxlength=%s' % (row[3])
                field_desc += ')'
                if field_type_was_guessed:
                    field_desc += ' # This is a guess!'
            yield '    %s' % field_desc
        yield '    class META:'
        yield '        db_table = %r' % table_name
        yield ''
inspectdb.help_doc = "Introspects the database tables in the given database and outputs a Django model module."
inspectdb.args = "[dbname]"

class ModelErrorCollection:
    def __init__(self, outfile=sys.stdout):
        self.errors = []
        self.outfile = outfile

    def add(self, opts, error):
        self.errors.append((opts, error))
        self.outfile.write("%s.%s: %s\n" % (opts.app_label, opts.module_name, error))

def get_validation_errors(outfile):
    "Validates all installed models. Writes errors, if any, to outfile. Returns number of errors."
    import django.models
    from django.core import meta
    e = ModelErrorCollection(outfile)
    module_list = meta.get_installed_model_modules()
    for module in module_list:
        for mod in module._MODELS:
            opts = mod._meta

            # Do field-specific validation.
            for f in opts.fields:
                if isinstance(f, meta.CharField) and f.maxlength in (None, 0):
                    e.add(opts, '"%s" field: CharFields require a "maxlength" attribute.' % f.name)
                if isinstance(f, meta.FloatField):
                    if f.decimal_places is None:
                        e.add(opts, '"%s" field: FloatFields require a "decimal_places" attribute.' % f.name)
                    if f.max_digits is None:
                        e.add(opts, '"%s" field: FloatFields require a "max_digits" attribute.' % f.name)
                if isinstance(f, meta.FileField) and not f.upload_to:
                    e.add(opts, '"%s" field: FileFields require an "upload_to" attribute.' % f.name)
                if isinstance(f, meta.ImageField):
                    try:
                        from PIL import Image
                    except ImportError:
                        e.add(opts, '"%s" field: To use ImageFields, you need to install the Python Imaging Library. Get it at http://www.pythonware.com/products/pil/ .')
                if f.prepopulate_from is not None and type(f.prepopulate_from) not in (list, tuple):
                    e.add(opts, '"%s" field: prepopulate_from should be a list or tuple.' % f.name)
                if f.choices:
                    if not type(f.choices) in (tuple, list):
                        e.add(opts, '"%s" field: "choices" should be either a tuple or list.' % f.name)
                    else:
                        for c in f.choices:
                            if not type(c) in (tuple, list) or len(c) != 2:
                                e.add(opts, '"%s" field: "choices" should be a sequence of two-tuples.' % f.name)

            # Check for multiple ManyToManyFields to the same object, and
            # verify "singular" is set in that case.
            for i, f in enumerate(opts.many_to_many):
                for previous_f in opts.many_to_many[:i]:
                    if f.rel.to == previous_f.rel.to and f.rel.singular == previous_f.rel.singular:
                        e.add(opts, 'The "%s" field requires a "singular" parameter, because the %s model has more than one ManyToManyField to the same model (%s).' % (f.name, opts.object_name, previous_f.rel.to.object_name))

            # Check admin attribute.
            if opts.admin is not None:
                if not isinstance(opts.admin, meta.Admin):
                    e.add(opts, '"admin" attribute, if given, must be set to a meta.Admin() instance.')
                else:
                    # list_display
                    if not isinstance(opts.admin.list_display, (list, tuple)):
                        e.add(opts, '"admin.list_display", if given, must be set to a list or tuple.')
                    else:
                        for fn in opts.admin.list_display:
                            try:
                                f = opts.get_field(fn)
                            except meta.FieldDoesNotExist:
                                klass = opts.get_model_module().Klass
                                if not hasattr(klass, fn) or not callable(getattr(klass, fn)):
                                    e.add(opts, '"admin.list_display" refers to %r, which isn\'t a field or method.' % fn)
                            else:
                                if isinstance(f, meta.ManyToManyField):
                                    e.add(opts, '"admin.list_display" doesn\'t support ManyToManyFields (%r).' % fn)
                    # list_filter
                    if not isinstance(opts.admin.list_filter, (list, tuple)):
                        e.add(opts, '"admin.list_filter", if given, must be set to a list or tuple.')
                    else:
                        for fn in opts.admin.list_filter:
                            try:
                                f = opts.get_field(fn)
                            except meta.FieldDoesNotExist:
                                e.add(opts, '"admin.list_filter" refers to %r, which isn\'t a field.' % fn)

            # Check ordering attribute.
            if opts.ordering:
                for field_name in opts.ordering:
                    if field_name == '?': continue
                    if field_name.startswith('-'):
                        field_name = field_name[1:]
                    if opts.order_with_respect_to and field_name == '_order':
                        continue
                    try:
                        opts.get_field(field_name, many_to_many=False)
                    except meta.FieldDoesNotExist:
                        e.add(opts, '"ordering" refers to "%s", a field that doesn\'t exist.' % field_name)

            # Check core=True, if needed.
            for related in opts.get_followed_related_objects():
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
                    except meta.FieldDoesNotExist:
                        e.add(opts, '"unique_together" refers to %s, a field that doesn\'t exist. Check your syntax.' % field_name)
                    else:
                        if isinstance(f.rel, meta.ManyToMany):
                            e.add(opts, '"unique_together" refers to %s. ManyToManyFields are not supported in unique_together.' % f.name)
    return len(e.errors)

def validate(outfile=sys.stdout):
    "Validates all installed models."
    num_errors = get_validation_errors(outfile)
    outfile.write('%s error%s found.\n' % (num_errors, num_errors != 1 and 's' or ''))
validate.args = ''

def runserver(addr, port):
    "Starts a lightweight Web server for development."
    from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
    from django.core.handlers.wsgi import WSGIHandler
    if not addr:
        addr = '127.0.0.1'
    if not port.isdigit():
        sys.stderr.write("Error: %r is not a valid port number.\n" % port)
        sys.exit(1)
    def inner_run():
        from django.conf.settings import SETTINGS_MODULE
        print "Validating models..."
        validate()
        print "\nStarting server on port %s with settings module %r." % (port, SETTINGS_MODULE)
        print "Go to http://%s:%s/ for Django." % (addr, port)
        print "Quit the server with CONTROL-C (Unix) or CTRL-BREAK (Windows)."
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
            sys.stderr.write("Error: %s\n" % error_text)
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(0)
    from django.utils import autoreload
    autoreload.main(inner_run)
runserver.args = '[optional port number, or ipaddr:port]'

def createcachetable(tablename):
    "Creates the table needed to use the SQL cache backend"
    from django.core import db, meta
    fields = (
        # "key" is a reserved word in MySQL, so use "cache_key" instead.
        meta.CharField(name='cache_key', maxlength=255, unique=True, primary_key=True),
        meta.TextField(name='value'),
        meta.DateTimeField(name='expires', db_index=True),
    )
    table_output = []
    index_output = []
    for f in fields:
        field_output = [db.db.quote_name(f.column), db.DATA_TYPES[f.get_internal_type()] % f.__dict__]
        field_output.append("%sNULL" % (not f.null and "NOT " or ""))
        if f.unique:
            field_output.append("UNIQUE")
        if f.primary_key:
            field_output.append("PRIMARY KEY")
        if f.db_index:
            unique = f.unique and "UNIQUE " or ""
            index_output.append("CREATE %sINDEX %s_%s ON %s (%s);" % \
                (unique, tablename, f.column, db.db.quote_name(tablename),
                db.db.quote_name(f.column)))
        table_output.append(" ".join(field_output))
    full_statement = ["CREATE TABLE %s (" % db.db.quote_name(tablename)]
    for i, line in enumerate(table_output):
        full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
    full_statement.append(');')
    curs = db.db.cursor()
    curs.execute("\n".join(full_statement))
    for statement in index_output:
        curs.execute(statement)
    db.db.commit()
createcachetable.args = "[tablename]"
