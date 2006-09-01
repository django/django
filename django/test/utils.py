import sys, time
from django.conf import settings
from django.db import connection, transaction, backend

# The prefix to put on the default database name when creating
# the test database.
TEST_DATABASE_PREFIX = 'test_'

def _set_autocommit(connection):
    "Make sure a connection is in autocommit mode."
    if hasattr(connection.connection, "autocommit"):
        connection.connection.autocommit(True)
    elif hasattr(connection.connection, "set_isolation_level"):
        connection.connection.set_isolation_level(0)

def create_test_db(verbosity=1, autoclobber=False):
    if verbosity >= 1:
        print "Creating test database..."
    # If we're using SQLite, it's more convenient to test against an
    # in-memory database.
    if settings.DATABASE_ENGINE == "sqlite3":
        TEST_DATABASE_NAME = ":memory:"
    else:
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
            cursor.execute("CREATE DATABASE %s" % backend.quote_name(TEST_DATABASE_NAME))
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
                    cursor.execute("CREATE DATABASE %s" % backend.quote_name(TEST_DATABASE_NAME))
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)
               
    connection.close()
    settings.DATABASE_NAME = TEST_DATABASE_NAME

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
    if settings.DATABASE_ENGINE != "sqlite3":
        connection.close()
        TEST_DATABASE_NAME = settings.DATABASE_NAME
        settings.DATABASE_NAME = old_database_name
        cursor = connection.cursor()
        _set_autocommit(connection)
        time.sleep(1) # To avoid "database is being accessed by other users" errors.
        cursor.execute("DROP DATABASE %s" % backend.quote_name(TEST_DATABASE_NAME))
        connection.close()

