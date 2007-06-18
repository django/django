import sys, time
from django.conf import settings
from django.db import connection, transaction, backend
from django.core import management, mail
from django.dispatch import dispatcher
from django.test import signals
from django.template import Template

# The prefix to put on the default database name when creating
# the test database.
TEST_DATABASE_PREFIX = 'test_'

def instrumented_test_render(self, context):
    """
    An instrumented Template render method, providing a signal that can be
    intercepted by the test system Client.
    """
    dispatcher.send(signal=signals.template_rendered, sender=self, template=self, context=context)
    return self.nodelist.render(context)

def instrumented_test_iter_render(self, context):
    """
    An instrumented Template iter_render method, providing a signal that can be
    intercepted by the test system Client.
    """
    for chunk in self.nodelist.iter_render(context):
        yield chunk
    dispatcher.send(signal=signals.template_rendered, sender=self, template=self, context=context)
    
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

def setup_test_environment():
    """Perform any global pre-test setup. This involves:
        
        - Installing the instrumented test renderer
        - Diverting the email sending functions to a test buffer
        
    """
    Template.original_render = Template.render
    Template.original_iter_render = Template.iter_render
    Template.render = instrumented_test_render
    Template.iter_render = instrumented_test_render
    
    mail.original_SMTPConnection = mail.SMTPConnection
    mail.SMTPConnection = TestSMTPConnection

    mail.outbox = []
    
def teardown_test_environment():
    """Perform any global post-test teardown. This involves:

        - Restoring the original test renderer
        - Restoring the email sending functions
        
    """
    Template.render = Template.original_render
    Template.iter_render = Template.original_iter_render
    del Template.original_render, Template.original_iter_render
    
    mail.SMTPConnection = mail.original_SMTPConnection
    del mail.original_SMTPConnection
    
    del mail.outbox
    
def _set_autocommit(connection):
    "Make sure a connection is in autocommit mode."
    if hasattr(connection.connection, "autocommit"):
        connection.connection.autocommit(True)
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
    if verbosity >= 1:
        print "Creating test database..."
    # If we're using SQLite, it's more convenient to test against an
    # in-memory database.
    if settings.DATABASE_ENGINE == "sqlite3":
        TEST_DATABASE_NAME = ":memory:"
    else:
        suffix = {
            'postgresql': get_postgresql_create_suffix,
            'postgresql_psycopg2': get_postgresql_create_suffix,
            'mysql': get_mysql_create_suffix,
            'mysql_old': get_mysql_create_suffix,
        }.get(settings.DATABASE_ENGINE, lambda: '')()
        if settings.TEST_DATABASE_NAME:
            TEST_DATABASE_NAME = settings.TEST_DATABASE_NAME
        else:
            TEST_DATABASE_NAME = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
        
        # Create the test database and connect to it. We need to autocommit
        # if the database supports it because PostgreSQL doesn't allow 
        # CREATE/DROP DATABASE statements within transactions.
        cursor = connection.cursor()
        _set_autocommit(connection)
        try:
            cursor.execute("CREATE DATABASE %s %s" % (backend.quote_name(TEST_DATABASE_NAME), suffix))
        except Exception, e:            
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print "Destroying old test database..."                
                    cursor.execute("DROP DATABASE %s" % backend.quote_name(TEST_DATABASE_NAME))
                    if verbosity >= 1:
                        print "Creating test database..."
                    cursor.execute("CREATE DATABASE %s %s" % (backend.quote_name(TEST_DATABASE_NAME), suffix))
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)
               
    connection.close()
    settings.DATABASE_NAME = TEST_DATABASE_NAME

    management.syncdb(verbosity, interactive=False)

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()

def destroy_test_db(old_database_name, verbosity=1):
    # Unless we're using SQLite, remove the test database to clean up after
    # ourselves. Connect to the previous database (not the test database)
    # to do so, because it's not allowed to delete a database while being
    # connected to it.
    if verbosity >= 1:
        print "Destroying test database..."
    connection.close()
    TEST_DATABASE_NAME = settings.DATABASE_NAME
    settings.DATABASE_NAME = old_database_name

    if settings.DATABASE_ENGINE != "sqlite3":
        cursor = connection.cursor()
        _set_autocommit(connection)
        time.sleep(1) # To avoid "database is being accessed by other users" errors.
        cursor.execute("DROP DATABASE %s" % backend.quote_name(TEST_DATABASE_NAME))
        connection.close()
