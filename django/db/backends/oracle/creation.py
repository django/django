import sys, time

# This dictionary maps Field objects to their associated Oracle column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':                    'NUMBER(11)',
    'BooleanField':                 'NUMBER(1) CHECK (%(column)s IN (0,1))',
    'CharField':                    'VARCHAR2(%(maxlength)s)',
    'CommaSeparatedIntegerField':   'VARCHAR2(%(maxlength)s)',
    'DateField':                    'DATE',
    'DateTimeField':                'TIMESTAMP',
    'FileField':                    'VARCHAR2(100)',
    'FilePathField':                'VARCHAR2(100)',
    'FloatField':                   'NUMBER(%(max_digits)s, %(decimal_places)s)',
    'ImageField':                   'VARCHAR2(100)',
    'IntegerField':                 'NUMBER(11)',
    'IPAddressField':               'CHAR(15)',
    'ManyToManyField':              None,
    'NullBooleanField':             'NUMBER(1) CHECK ((%(column)s IN (0,1)) OR (%(column)s IS NULL))',
    'OneToOneField':                'NUMBER(11)',
    'PhoneNumberField':             'VARCHAR2(20)',
    'PositiveIntegerField':         'NUMBER(11) CHECK (%(column)s >= 1)',
    'PositiveSmallIntegerField':    'NUMBER(11) CHECK (%(column)s >= 1)',
    'SlugField':                    'VARCHAR2(50)',
    'SmallIntegerField':            'NUMBER(11)',
    'TextField':                    'NCLOB',
    'TimeField':                    'TIMESTAMP',
    'URLField':                     'VARCHAR2(200)',
    'USStateField':                 'CHAR(2)',
}

TEST_DATABASE_PREFIX = 'test_'
PASSWORD = 'Im_a_lumberjack'
OLD_DATABASE_USER = None
OLD_DATABASE_PASSWORD = None

def create_test_db(settings, connection, backend, verbosity=1, autoclobber=False):
    if verbosity >= 1:
        print "Creating test database..."

    TEST_DATABASE_NAME = _test_database_name(settings)

    cursor = connection.cursor()
    try:
        _create_test_db(cursor, TEST_DATABASE_NAME, verbosity)
    except Exception, e:
        sys.stderr.write("Got an error creating the test database: %s\n" % e)
        if not autoclobber:
            confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
        if autoclobber or confirm == 'yes':
            try:
                if verbosity >= 1:
                    print "Destroying old test database..."
                _destroy_test_db(cursor, TEST_DATABASE_NAME, verbosity)
                if verbosity >= 1:
                    print "Creating test database..."
                _create_test_db(cursor, TEST_DATABASE_NAME, verbosity)
            except Exception, e:
                sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                sys.exit(2)
        else:
            print "Tests cancelled."
            sys.exit(1)

    connection.close()
    settings.DATABASE_USER = TEST_DATABASE_NAME
    settings.DATABASE_PASSWORD = PASSWORD

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()

def destroy_test_db(settings, connection, backend, old_database_name, verbosity=1):
    if verbosity >= 1:
        print "Destroying test database..."
    connection.close()

    TEST_DATABASE_NAME = _test_database_name(settings)
    settings.DATABASE_NAME = old_database_name
    #settings.DATABASE_USER = 'old_user'
    #settings.DATABASE_PASSWORD = 'old_password'
    settings.DATABASE_USER = 'mboersma'
    settings.DATABASE_PASSWORD = 'password'

    cursor = connection.cursor()
    time.sleep(1) # To avoid "database is being accessed by other users" errors.
    _destroy_test_db(cursor, TEST_DATABASE_NAME, verbosity)
    connection.close()

def _create_test_db(cursor, dbname, verbosity):
    if verbosity >= 2:
        print "_create_test_db(): dbname = %s" % dbname
    statements = [
        """CREATE TABLESPACE %(user)s
           DATAFILE '%(user)s.dbf' SIZE 10M AUTOEXTEND ON NEXT 10M MAXSIZE 20M
        """,
        """CREATE TEMPORARY TABLESPACE %(user)s_temp
           TEMPFILE '%(user)s_temp.dbf' SIZE 10M AUTOEXTEND ON NEXT 10M MAXSIZE 20M
        """,
        """CREATE USER %(user)s
           IDENTIFIED BY %(password)s
           DEFAULT TABLESPACE %(user)s
           TEMPORARY TABLESPACE %(user)s_temp
        """,
        """GRANT CONNECT, RESOURCE TO %(user)s""",
    ]
    _execute_statements(cursor, statements, dbname, verbosity)

def _destroy_test_db(cursor, dbname, verbosity):
    if verbosity >= 2:
        print "_destroy_test_db(): dbname=%s" % dbname
    statements = [
        'DROP USER %(user)s CASCADE',
        'DROP TABLESPACE %(user)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
        'DROP TABLESPACE %(user)s_TEMP INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
        ]
    _execute_statements(cursor, statements, dbname, verbosity)

def _execute_statements(cursor, statements, dbname, verbosity):
    for template in statements:
        stmt = template % {'user': dbname,
			   'password': PASSWORD}
        if verbosity >= 2:
            print stmt
        try:
            cursor.execute(stmt)
        except Exception, err:
            sys.stderr.write("Failed (%s)\n" % (err))
            raise

def _test_database_name(settings):
    if settings.TEST_DATABASE_NAME:
        name = settings.TEST_DATABASE_NAME
    else:
        name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
    return name
