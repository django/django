import os
from django.conf import settings
from django.core.management import call_command
from django.db import connection

def spatialite_init_file():
    # SPATIALITE_SQL may be placed in settings to tell
    # GeoDjango to use a specific user-supplied file.
    return getattr(settings, 'SPATIALITE_SQL', 'init_spatialite-2.3.sql')

def create_test_spatial_db(verbosity=1, autoclobber=False, interactive=False):
    "Creates a spatial database based on the settings."

    # Making sure we're using PostgreSQL and psycopg2
    if settings.DATABASE_ENGINE != 'sqlite3':
        raise Exception('SpatiaLite database creation only supported on sqlite3 platform.')

    # Getting the test database name using the the SQLite backend's
    # `_create_test_db`.  Unless `TEST_DATABASE_NAME` is defined,
    # it returns ":memory:".
    db_name = connection.creation._create_test_db(verbosity, autoclobber)

    # Closing out the current connection to the database set in
    # originally in the settings.  This makes it so `initialize_spatialite`
    # function will be run on the connection for the _test_ database instead.
    connection.close()

    # Point to the new database
    settings.DATABASE_NAME = db_name
    connection.settings_dict["DATABASE_NAME"] = db_name
    can_rollback = connection.creation._rollback_works()
    settings.DATABASE_SUPPORTS_TRANSACTIONS = can_rollback
    connection.settings_dict["DATABASE_SUPPORTS_TRANSACTIONS"] = can_rollback

    # Finally, loading up the SpatiaLite SQL file.
    load_spatialite_sql(db_name, verbosity=verbosity)

    if verbosity >= 1:
        print 'Creation of spatial database %s successful.' % db_name

    # Syncing the database
    call_command('syncdb', verbosity=verbosity, interactive=interactive)

def load_spatialite_sql(db_name, verbosity=1):
    """
    This routine loads up the SpatiaLite SQL file.
    """
    # Getting the location of the SpatiaLite SQL file, and confirming
    # it exists.
    spatialite_sql = spatialite_init_file()
    if not os.path.isfile(spatialite_sql):
        raise Exception('Could not find the SpatiaLite initialization SQL file: %s' % spatialite_sql)

    # Opening up the SpatiaLite SQL initialization file and executing
    # as a script.
    sql_fh = open(spatialite_sql, 'r')
    try:
        cur = connection.cursor()
        cur.executescript(sql_fh.read())
    finally:
        sql_fh.close()
