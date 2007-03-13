import sys, time
from django.core import management

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
REMEMBER = {}


def create_test_db(settings, connection, backend, verbosity=1, autoclobber=False):

    TEST_DATABASE_NAME = _test_database_name(settings)
    TEST_DATABASE_USER = _test_database_user(settings)
    TEST_DATABASE_PASSWD = _test_database_passwd(settings)
    TEST_DATABASE_TBLSPACE = _test_database_tblspace(settings)
    TEST_DATABASE_TBLSPACE_TMP = _test_database_tblspace_tmp(settings)

    parameters = {
        'dbname': TEST_DATABASE_NAME,
        'user': TEST_DATABASE_USER,
        'password': TEST_DATABASE_PASSWD,
        'tblspace': TEST_DATABASE_TBLSPACE,
        'tblspace_temp': TEST_DATABASE_TBLSPACE_TMP,
 	}

    REMEMBER['user'] = settings.DATABASE_USER
    REMEMBER['passwd'] = settings.DATABASE_PASSWORD

    cursor = connection.cursor()
    if _test_database_create(settings):
        if verbosity >= 1:
            print 'Creating test database...'
        try:
            _create_test_db(cursor, parameters, verbosity)
        except Exception, e:
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_NAME)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print "Destroying old test database..."
                    _destroy_test_db(cursor, parameters, verbosity)
                    if verbosity >= 1:
                        print "Creating test database..."
                    _create_test_db(cursor, parameters, verbosity)
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)

    if _test_user_create(settings):
        if verbosity >= 1:
            print "Creating test user..."
        try:
            _create_test_user(cursor, parameters, verbosity)
        except Exception, e:
            sys.stderr.write("Got an error creating the test user: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("It appears the test user, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_DATABASE_USER)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print "Destroying old test user..."
                    _destroy_test_user(cursor, parameters, verbosity)
                    if verbosity >= 1:
                        print "Creating test user..."
                    _create_test_user(cursor, parameters, verbosity)
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test user: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)

    connection.close()
    settings.DATABASE_USER = TEST_DATABASE_USER
    settings.DATABASE_PASSWORD = TEST_DATABASE_PASSWD

    management.syncdb(verbosity, interactive=False)

    # Get a cursor (even though we don't need one yet). This has
    # the side effect of initializing the test database.
    cursor = connection.cursor()


def destroy_test_db(settings, connection, backend, old_database_name, verbosity=1):
    connection.close()

    TEST_DATABASE_NAME = _test_database_name(settings)
    TEST_DATABASE_USER = _test_database_user(settings)
    TEST_DATABASE_PASSWD = _test_database_passwd(settings)
    TEST_DATABASE_TBLSPACE = _test_database_tblspace(settings)
    TEST_DATABASE_TBLSPACE_TMP = _test_database_tblspace_tmp(settings)

    settings.DATABASE_NAME = old_database_name
    settings.DATABASE_USER = REMEMBER['user']
    settings.DATABASE_PASSWORD = REMEMBER['passwd']

    parameters = {
        'dbname': TEST_DATABASE_NAME,
        'user': TEST_DATABASE_USER,
        'password': TEST_DATABASE_PASSWD,
        'tblspace': TEST_DATABASE_TBLSPACE,
        'tblspace_temp': TEST_DATABASE_TBLSPACE_TMP,
 	}

    REMEMBER['user'] = settings.DATABASE_USER
    REMEMBER['passwd'] = settings.DATABASE_PASSWORD

    cursor = connection.cursor()
    time.sleep(1) # To avoid "database is being accessed by other users" errors.
    if _test_user_create(settings):
        if verbosity >= 1:
            print 'Destroying test user...'
        _destroy_test_user(cursor, parameters, verbosity)
    if _test_database_create(settings):
        if verbosity >= 1:
            print 'Destroying test database...'
        _destroy_test_db(cursor, parameters, verbosity)
    connection.close()


def _create_test_db(cursor, parameters, verbosity):
    if verbosity >= 2:
        print "_create_test_db(): dbname = %s" % parameters['dbname']
    statements = [
        """CREATE TABLESPACE %(tblspace)s
           DATAFILE '%(tblspace)s.dbf' SIZE 10M AUTOEXTEND ON NEXT 10M MAXSIZE 20M
        """,
        """CREATE TEMPORARY TABLESPACE %(tblspace_temp)s
           TEMPFILE '%(tblspace_temp)s.dbf' SIZE 10M AUTOEXTEND ON NEXT 10M MAXSIZE 20M
        """,
    ]
    _execute_statements(cursor, statements, parameters, verbosity)


def _create_test_user(cursor, parameters, verbosity):
    if verbosity >= 2:
        print "_create_test_user(): username = %s" % parameters['user']
    statements = [
        """CREATE USER %(user)s
           IDENTIFIED BY %(password)s
           DEFAULT TABLESPACE %(tblspace)s
           TEMPORARY TABLESPACE %(tblspace_temp)s
        """,
        """GRANT CONNECT, RESOURCE TO %(user)s""",
    ]
    _execute_statements(cursor, statements, parameters, verbosity)


def _destroy_test_db(cursor, parameters, verbosity):
    if verbosity >= 2:
        print "_destroy_test_db(): dbname=%s" % parameters['dbname']
    statements = [
        'DROP TABLESPACE %(tblspace)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
        'DROP TABLESPACE %(tblspace_temp)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
        ]
    _execute_statements(cursor, statements, parameters, verbosity)


def _destroy_test_user(cursor, parameters, verbosity):
    if verbosity >= 2:
        print "_destroy_test_user(): user=%s" % parameters['user']
        print "Be patient.  This can take some time..."
    statements = [
        'DROP USER %(user)s CASCADE',
    ]
    _execute_statements(cursor, statements, parameters, verbosity)


def _execute_statements(cursor, statements, parameters, verbosity):
    for template in statements:
        stmt = template % parameters
        if verbosity >= 2:
            print stmt
        try:
            cursor.execute(stmt)
        except Exception, err:
            sys.stderr.write("Failed (%s)\n" % (err))
            raise


def _test_database_name(settings):
    name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
    try:
        if settings.TEST_DATABASE_NAME:
            name = settings.TEST_DATABASE_NAME
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_database_create(settings):
    name = True
    try:
        if settings.TEST_DATABASE_CREATE:
            name = True
        else:
            name = False
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_user_create(settings):
    name = True
    try:
        if settings.TEST_USER_CREATE:
            name = True
        else:
            name = False
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_database_user(settings):
    name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
    try:
        if settings.TEST_DATABASE_USER:
            name = settings.TEST_DATABASE_USER
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_database_passwd(settings):
    name = PASSWORD
    try:
        if settings.TEST_DATABASE_PASSWD:
            name = settings.TEST_DATABASE_PASSWD
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_database_tblspace(settings):
    name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
    try:
        if settings.TEST_DATABASE_TBLSPACE:
            name = settings.TEST_DATABASE_TBLSPACE
    except AttributeError:
        pass
    except:
        raise
    return name


def _test_database_tblspace_tmp(settings):
    name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME + '_temp'
    try:
        if settings.TEST_DATABASE_TBLSPACE_TMP:
            name = settings.TEST_DATABASE_TBLSPACE_TMP
    except AttributeError:
        pass
    except:
        raise
    return name
