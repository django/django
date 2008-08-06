import sys, time, os
from django.conf import settings
from django.db import connection, get_creation_module
from django.core import mail
from django.core.management import call_command
from django.test import signals
from django.template import Template
from django.utils.translation import deactivate

# The prefix to put on the default database name when creating
# the test database.
TEST_DATABASE_PREFIX = 'test_'

def instrumented_test_render(self, context):
    """
    An instrumented Template render method, providing a signal
    that can be intercepted by the test system Client
    """
    signals.template_rendered.send(sender=self, template=self, context=context)
    return self.nodelist.render(context)

class TestSMTPConnection(object):
    """A substitute SMTP connection for use during test sessions.
    The test connection stores email messages in a dummy outbox,
    rather than sending them out on the wire.

    """
    def __init__(*args, **kwargs):
        pass
    def open(self):
        "Mock the SMTPConnection open() interface"
        pass
    def close(self):
        "Mock the SMTPConnection close() interface"
        pass
    def send_messages(self, messages):
        "Redirect messages to the dummy outbox"
        mail.outbox.extend(messages)
        return len(messages)

def setup_test_environment():
    """Perform any global pre-test setup. This involves:

        - Installing the instrumented test renderer
        - Diverting the email sending functions to a test buffer
        - Setting the active locale to match the LANGUAGE_CODE setting.
    """
    Template.original_render = Template.render
    Template.render = instrumented_test_render

    mail.original_SMTPConnection = mail.SMTPConnection
    mail.SMTPConnection = TestSMTPConnection

    mail.outbox = []

    deactivate()

def teardown_test_environment():
    """Perform any global post-test teardown. This involves:

        - Restoring the original test renderer
        - Restoring the email sending functions

    """
    Template.render = Template.original_render
    del Template.original_render

    mail.SMTPConnection = mail.original_SMTPConnection
    del mail.original_SMTPConnection

    del mail.outbox

def _set_autocommit(connection):
    "Make sure a connection is in autocommit mode."
    if hasattr(connection.connection, "autocommit"):
        if callable(connection.connection.autocommit):
            connection.connection.autocommit(True)
        else:
            connection.connection.autocommit = True
    elif hasattr(connection.connection, "set_isolation_level"):
        connection.connection.set_isolation_level(0)

def get_mysql_create_suffix():
    suffix = []
    if settings.TEST_DATABASE_CHARSET:
        suffix.append('CHARACTER SET %s' % settings.TEST_DATABASE_CHARSET)
    if settings.TEST_DATABASE_COLLATION:
        suffix.append('COLLATE %s' % settings.TEST_DATABASE_COLLATION)
    return ' '.join(suffix)

def get_postgresql_create_suffix():
    assert settings.TEST_DATABASE_COLLATION is None, "PostgreSQL does not support collation setting at database creation time."
    if settings.TEST_DATABASE_CHARSET:
        return "WITH ENCODING '%s'" % settings.TEST_DATABASE_CHARSET
    return ''

def create_test_db(verbosity=1, autoclobber=False):
    """
    Creates a test database, prompting the user for confirmation if the
    database already exists. Returns the name of the test database created.
    """
    # If the database backend wants to create the test DB itself, let it
    creation_module = get_creation_module()
    if hasattr(creation_module, "create_test_db"):
        creation_module.create_test_db(settings, connection, verbosity, autoclobber)
        return

    if verbosity >= 1:
        print "Creating test database..."
    # If we're using SQLite, it's more convenient to test against an
    # in-memory database. Using the TEST_DATABASE_NAME setting you can still choose
    # to run on a physical database.
    if settings.DATABASE_ENGINE == "sqlite3":
        if settings.TEST_DATABASE_NAME and settings.TEST_DATABASE_NAME != ":memory:":
            TEST_DATABASE_NAME = settings.TEST_DATABASE_NAME
            # Erase the old test database
            if verbosity >= 1:
                print "Destroying old test database..."
            if os.access(TEST_DATABASE_NAME, os.F_OK):
                if not autoclobber:
                    confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % TEST_DATABASE_NAME)
                if autoclobber or confirm == 'yes':
                  try:
                      if verbosity >= 1:
                          print "Destroying old test database..."
                      os.remove(TEST_DATABASE_NAME)
                  except Exception, e:
                      sys.stderr.write("Got an error deleting the old test database: %s\n" % e)
                      sys.exit(2)
                else:
                    print "Tests cancelled."
                    sys.exit(1)
            if verbosity >= 1:
                print "Creating test database..."
        else:
            TEST_DATABASE_NAME = ":memory:"
    else:
        suffix = {
            'postgresql': get_postgresql_create_suffix,
            'postgresql_psycopg2': get_postgresql_create_suffix,
            'mysql': get_mysql_create_suffix,
        }.get(settings.DATABASE_ENGINE, lambda: '')()
        if settings.TEST_DATABASE_NAME:
            TEST_DATABASE_NAME = settings.TEST_DATABASE_NAME
        else:
            TEST_DATABASE_NAME = TEST_DATABASE_PREFIX + settings.DATABASE_NAME

        qn = connection.ops.quote_name

        # Create the test database and connect to it. We need to autocommit
        # if the database supports it because PostgreSQL doesn't allow
        # CREATE/DROP DATABASE statements within transactions.
        cursor = connection.cursor()
        _set_autocommit(connection)
        try:
            cursor.execute("CREATE DATABASE %s %s" % (qn(TEST_DATABASE_NAME), suffix))
        except Exception, e:
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % TEST_DATABASE_NAME)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print "Destroying old test database..."
                    cursor.execute("DROP DATABASE %s" % qn(TEST_DATABASE_NAME))
                    if verbosity >= 1:
                        print "Creating test database..."
                    cursor.execute("CREATE DATABASE %s %s" % (qn(TEST_DATABASE_NAME), suffix))
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)

    connection.close()
    settings.DATABASE_NAME = TEST_DATABASE_NAME

    call_command('syncdb', verbosity=verbosity, interactive=False)

    if settings.CACHE_BACKEND.startswith('db://'):
        cache_name = settings.CACHE_BACKEND[len('db://'):]
        call_command('createcachetable', cache_name)

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()

    return TEST_DATABASE_NAME

def destroy_test_db(old_database_name, verbosity=1):
    # If the database wants to drop the test DB itself, let it
    creation_module = get_creation_module()
    if hasattr(creation_module, "destroy_test_db"):
        creation_module.destroy_test_db(settings, connection, old_database_name, verbosity)
        return

    if verbosity >= 1:
        print "Destroying test database..."
    connection.close()
    TEST_DATABASE_NAME = settings.DATABASE_NAME
    settings.DATABASE_NAME = old_database_name
    if settings.DATABASE_ENGINE == "sqlite3":
        if TEST_DATABASE_NAME and TEST_DATABASE_NAME != ":memory:":
            # Remove the SQLite database file
            os.remove(TEST_DATABASE_NAME)
    else:
        # Remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        cursor = connection.cursor()
        _set_autocommit(connection)
        time.sleep(1) # To avoid "database is being accessed by other users" errors.
        cursor.execute("DROP DATABASE %s" % connection.ops.quote_name(TEST_DATABASE_NAME))
        connection.close()
