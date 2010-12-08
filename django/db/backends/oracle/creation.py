import sys, time
from django.db.backends.creation import BaseDatabaseCreation

TEST_DATABASE_PREFIX = 'test_'
PASSWORD = 'Im_a_lumberjack'

class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated Oracle column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    #
    # Any format strings starting with "qn_" are quoted before being used in the
    # output (the "qn_" prefix is stripped before the lookup is performed.

    data_types = {
        'AutoField':                    'NUMBER(11)',
        'BooleanField':                 'NUMBER(1) CHECK (%(qn_column)s IN (0,1))',
        'CharField':                    'NVARCHAR2(%(max_length)s)',
        'CommaSeparatedIntegerField':   'VARCHAR2(%(max_length)s)',
        'DateField':                    'DATE',
        'DateTimeField':                'TIMESTAMP',
        'DecimalField':                 'NUMBER(%(max_digits)s, %(decimal_places)s)',
        'FileField':                    'NVARCHAR2(%(max_length)s)',
        'FilePathField':                'NVARCHAR2(%(max_length)s)',
        'FloatField':                   'DOUBLE PRECISION',
        'IntegerField':                 'NUMBER(11)',
        'BigIntegerField':              'NUMBER(19)',
        'IPAddressField':               'VARCHAR2(15)',
        'NullBooleanField':             'NUMBER(1) CHECK ((%(qn_column)s IN (0,1)) OR (%(qn_column)s IS NULL))',
        'OneToOneField':                'NUMBER(11)',
        'PositiveIntegerField':         'NUMBER(11) CHECK (%(qn_column)s >= 0)',
        'PositiveSmallIntegerField':    'NUMBER(11) CHECK (%(qn_column)s >= 0)',
        'SlugField':                    'NVARCHAR2(%(max_length)s)',
        'SmallIntegerField':            'NUMBER(11)',
        'TextField':                    'NCLOB',
        'TimeField':                    'TIMESTAMP',
        'URLField':                     'VARCHAR2(%(max_length)s)',
    }

    def __init__(self, connection):
        self.remember = {}
        super(DatabaseCreation, self).__init__(connection)

    def _create_test_db(self, verbosity=1, autoclobber=False):
        TEST_NAME = self._get_test_db_name()
        TEST_USER = self._test_database_user()
        TEST_PASSWD = self._test_database_passwd()
        TEST_TBLSPACE = self._test_database_tblspace()
        TEST_TBLSPACE_TMP = self._test_database_tblspace_tmp()

        parameters = {
            'dbname': TEST_NAME,
            'user': TEST_USER,
            'password': TEST_PASSWD,
            'tblspace': TEST_TBLSPACE,
            'tblspace_temp': TEST_TBLSPACE_TMP,
        }

        self.remember['user'] = self.connection.settings_dict['USER']
        self.remember['passwd'] = self.connection.settings_dict['PASSWORD']

        cursor = self.connection.cursor()
        if self._test_database_create():
            try:
                self._execute_test_db_creation(cursor, parameters, verbosity)
            except Exception, e:
                sys.stderr.write("Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = raw_input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_NAME)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print "Destroying old test database '%s'..." % self.connection.alias
                        self._execute_test_db_destruction(cursor, parameters, verbosity)
                        self._execute_test_db_creation(cursor, parameters, verbosity)
                    except Exception, e:
                        sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print "Tests cancelled."
                    sys.exit(1)

        if self._test_user_create():
            if verbosity >= 1:
                print "Creating test user..."
            try:
                self._create_test_user(cursor, parameters, verbosity)
            except Exception, e:
                sys.stderr.write("Got an error creating the test user: %s\n" % e)
                if not autoclobber:
                    confirm = raw_input("It appears the test user, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_USER)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print "Destroying old test user..."
                        self._destroy_test_user(cursor, parameters, verbosity)
                        if verbosity >= 1:
                            print "Creating test user..."
                        self._create_test_user(cursor, parameters, verbosity)
                    except Exception, e:
                        sys.stderr.write("Got an error recreating the test user: %s\n" % e)
                        sys.exit(2)
                else:
                    print "Tests cancelled."
                    sys.exit(1)

        self.connection.settings_dict['TEST_USER'] = self.connection.settings_dict["USER"] = TEST_USER
        self.connection.settings_dict["PASSWORD"] = TEST_PASSWD

        return self.connection.settings_dict['NAME']

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        TEST_NAME = self._test_database_name()
        TEST_USER = self._test_database_user()
        TEST_PASSWD = self._test_database_passwd()
        TEST_TBLSPACE = self._test_database_tblspace()
        TEST_TBLSPACE_TMP = self._test_database_tblspace_tmp()

        self.connection.settings_dict["USER"] = self.remember['user']
        self.connection.settings_dict["PASSWORD"] = self.remember['passwd']

        parameters = {
            'dbname': TEST_NAME,
            'user': TEST_USER,
            'password': TEST_PASSWD,
            'tblspace': TEST_TBLSPACE,
            'tblspace_temp': TEST_TBLSPACE_TMP,
        }

        cursor = self.connection.cursor()
        time.sleep(1) # To avoid "database is being accessed by other users" errors.
        if self._test_user_create():
            if verbosity >= 1:
                print 'Destroying test user...'
            self._destroy_test_user(cursor, parameters, verbosity)
        if self._test_database_create():
            if verbosity >= 1:
                print 'Destroying test database tables...'
            self._execute_test_db_destruction(cursor, parameters, verbosity)
        self.connection.close()

    def _execute_test_db_creation(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print "_create_test_db(): dbname = %s" % parameters['dbname']
        statements = [
            """CREATE TABLESPACE %(tblspace)s
               DATAFILE '%(tblspace)s.dbf' SIZE 20M
               REUSE AUTOEXTEND ON NEXT 10M MAXSIZE 200M
            """,
            """CREATE TEMPORARY TABLESPACE %(tblspace_temp)s
               TEMPFILE '%(tblspace_temp)s.dbf' SIZE 20M
               REUSE AUTOEXTEND ON NEXT 10M MAXSIZE 100M
            """,
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _create_test_user(self, cursor, parameters, verbosity):
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
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _execute_test_db_destruction(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print "_execute_test_db_destruction(): dbname=%s" % parameters['dbname']
        statements = [
            'DROP TABLESPACE %(tblspace)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
            'DROP TABLESPACE %(tblspace_temp)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
            ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _destroy_test_user(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print "_destroy_test_user(): user=%s" % parameters['user']
            print "Be patient.  This can take some time..."
        statements = [
            'DROP USER %(user)s CASCADE',
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _execute_statements(self, cursor, statements, parameters, verbosity):
        for template in statements:
            stmt = template % parameters
            if verbosity >= 2:
                print stmt
            try:
                cursor.execute(stmt)
            except Exception, err:
                sys.stderr.write("Failed (%s)\n" % (err))
                raise

    def _get_test_db_name(self):
        name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        try:
            if self.connection.settings_dict['TEST_NAME']:
                name = self.connection.settings_dict['TEST_NAME']
        except AttributeError:
            pass
        return name

    def _test_database_create(self):
        return self.connection.settings_dict.get('TEST_CREATE', True)

    def _test_user_create(self):
        return self.connection.settings_dict.get('TEST_USER_CREATE', True)

    def _test_database_user(self):
        name = TEST_DATABASE_PREFIX + self.connection.settings_dict['USER']
        try:
            if self.connection.settings_dict['TEST_USER']:
                name = self.connection.settings_dict['TEST_USER']
        except KeyError:
            pass
        return name

    def _test_database_passwd(self):
        name = PASSWORD
        try:
            if self.connection.settings_dict['TEST_PASSWD']:
                name = self.connection.settings_dict['TEST_PASSWD']
        except KeyError:
            pass
        return name

    def _test_database_tblspace(self):
        name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
        try:
            if self.connection.settings_dict['TEST_TBLSPACE']:
                name = self.connection.settings_dict['TEST_TBLSPACE']
        except KeyError:
            pass
        return name

    def _test_database_tblspace_tmp(self):
        name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME'] + '_temp'
        try:
            if self.connection.settings_dict['TEST_TBLSPACE_TMP']:
                name = self.connection.settings_dict['TEST_TBLSPACE_TMP']
        except KeyError:
            pass
        return name
