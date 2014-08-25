import sys
import time

from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation
from django.utils.six.moves import input


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
        'AutoField': 'NUMBER(11)',
        'BinaryField': 'BLOB',
        'BooleanField': 'NUMBER(1)',
        'CharField': 'NVARCHAR2(%(max_length)s)',
        'CommaSeparatedIntegerField': 'VARCHAR2(%(max_length)s)',
        'DateField': 'DATE',
        'DateTimeField': 'TIMESTAMP',
        'DecimalField': 'NUMBER(%(max_digits)s, %(decimal_places)s)',
        'FileField': 'NVARCHAR2(%(max_length)s)',
        'FilePathField': 'NVARCHAR2(%(max_length)s)',
        'FloatField': 'DOUBLE PRECISION',
        'IntegerField': 'NUMBER(11)',
        'BigIntegerField': 'NUMBER(19)',
        'IPAddressField': 'VARCHAR2(15)',
        'GenericIPAddressField': 'VARCHAR2(39)',
        'NullBooleanField': 'NUMBER(1)',
        'OneToOneField': 'NUMBER(11)',
        'PositiveIntegerField': 'NUMBER(11)',
        'PositiveSmallIntegerField': 'NUMBER(11)',
        'SlugField': 'NVARCHAR2(%(max_length)s)',
        'SmallIntegerField': 'NUMBER(11)',
        'TextField': 'NCLOB',
        'TimeField': 'TIMESTAMP',
        'URLField': 'VARCHAR2(%(max_length)s)',
    }

    data_type_check_constraints = {
        'BooleanField': '%(qn_column)s IN (0,1)',
        'NullBooleanField': '(%(qn_column)s IN (0,1)) OR (%(qn_column)s IS NULL)',
        'PositiveIntegerField': '%(qn_column)s >= 0',
        'PositiveSmallIntegerField': '%(qn_column)s >= 0',
    }

    def __init__(self, connection):
        super(DatabaseCreation, self).__init__(connection)

    def _create_test_db(self, verbosity=1, autoclobber=False):
        TEST_NAME = self._test_database_name()
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

        cursor = self.connection.cursor()
        if self._test_database_create():
            try:
                self._execute_test_db_creation(cursor, parameters, verbosity)
            except Exception as e:
                sys.stderr.write("Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = input("It appears the test database, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_NAME)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test database '%s'..." % self.connection.alias)
                        self._execute_test_db_destruction(cursor, parameters, verbosity)
                        self._execute_test_db_creation(cursor, parameters, verbosity)
                    except Exception as e:
                        sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

        if self._test_user_create():
            if verbosity >= 1:
                print("Creating test user...")
            try:
                self._create_test_user(cursor, parameters, verbosity)
            except Exception as e:
                sys.stderr.write("Got an error creating the test user: %s\n" % e)
                if not autoclobber:
                    confirm = input("It appears the test user, %s, already exists. Type 'yes' to delete it, or 'no' to cancel: " % TEST_USER)
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test user...")
                        self._destroy_test_user(cursor, parameters, verbosity)
                        if verbosity >= 1:
                            print("Creating test user...")
                        self._create_test_user(cursor, parameters, verbosity)
                    except Exception as e:
                        sys.stderr.write("Got an error recreating the test user: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

        self.connection.close()  # done with main user -- test user and tablespaces created

        real_settings = settings.DATABASES[self.connection.alias]
        real_settings['SAVED_USER'] = self.connection.settings_dict['SAVED_USER'] = self.connection.settings_dict['USER']
        real_settings['SAVED_PASSWORD'] = self.connection.settings_dict['SAVED_PASSWORD'] = self.connection.settings_dict['PASSWORD']
        real_test_settings = real_settings['TEST']
        test_settings = self.connection.settings_dict['TEST']
        real_test_settings['USER'] = real_settings['USER'] = test_settings['USER'] = self.connection.settings_dict['USER'] = TEST_USER
        real_settings['PASSWORD'] = self.connection.settings_dict['PASSWORD'] = TEST_PASSWD

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

        self.connection.settings_dict['USER'] = self.connection.settings_dict['SAVED_USER']
        self.connection.settings_dict['PASSWORD'] = self.connection.settings_dict['SAVED_PASSWORD']

        parameters = {
            'dbname': TEST_NAME,
            'user': TEST_USER,
            'password': TEST_PASSWD,
            'tblspace': TEST_TBLSPACE,
            'tblspace_temp': TEST_TBLSPACE_TMP,
        }

        cursor = self.connection.cursor()
        time.sleep(1)  # To avoid "database is being accessed by other users" errors.
        if self._test_user_create():
            if verbosity >= 1:
                print('Destroying test user...')
            self._destroy_test_user(cursor, parameters, verbosity)
        if self._test_database_create():
            if verbosity >= 1:
                print('Destroying test database tables...')
            self._execute_test_db_destruction(cursor, parameters, verbosity)
        self.connection.close()

    def _execute_test_db_creation(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print("_create_test_db(): dbname = %s" % parameters['dbname'])
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
            print("_create_test_user(): username = %s" % parameters['user'])
        statements = [
            """CREATE USER %(user)s
               IDENTIFIED BY %(password)s
               DEFAULT TABLESPACE %(tblspace)s
               TEMPORARY TABLESPACE %(tblspace_temp)s
               QUOTA UNLIMITED ON %(tblspace)s
            """,
            """GRANT CONNECT, RESOURCE TO %(user)s""",
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _execute_test_db_destruction(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print("_execute_test_db_destruction(): dbname=%s" % parameters['dbname'])
        statements = [
            'DROP TABLESPACE %(tblspace)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
            'DROP TABLESPACE %(tblspace_temp)s INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS',
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _destroy_test_user(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print("_destroy_test_user(): user=%s" % parameters['user'])
            print("Be patient.  This can take some time...")
        statements = [
            'DROP USER %(user)s CASCADE',
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _execute_statements(self, cursor, statements, parameters, verbosity):
        for template in statements:
            stmt = template % parameters
            if verbosity >= 2:
                print(stmt)
            try:
                cursor.execute(stmt)
            except Exception as err:
                sys.stderr.write("Failed (%s)\n" % (err))
                raise

    def _test_settings_get(self, key, default=None, prefixed=None):
        """
        Return a value from the test settings dict,
        or a given default,
        or a prefixed entry from the main settings dict
        """
        settings_dict = self.connection.settings_dict
        val = settings_dict['TEST'].get(key, default)
        if val is None:
            val = TEST_DATABASE_PREFIX + settings_dict[prefixed]
        return val

    def _test_database_name(self):
        return self._test_settings_get('NAME', prefixed='NAME')

    def _test_database_create(self):
        return self._test_settings_get('CREATE_DB', default=True)

    def _test_user_create(self):
        return self._test_settings_get('CREATE_USER', default=True)

    def _test_database_user(self):
        return self._test_settings_get('USER', prefixed='USER')

    def _test_database_passwd(self):
        return self._test_settings_get('PASSWORD', default=PASSWORD)

    def _test_database_tblspace(self):
        return self._test_settings_get('TBLSPACE', prefixed='NAME')

    def _test_database_tblspace_tmp(self):
        settings_dict = self.connection.settings_dict
        return settings_dict['TEST'].get('TBLSPACE_TMP',
                                         TEST_DATABASE_PREFIX + settings_dict['NAME'] + '_temp')

    def _get_test_db_name(self):
        """
        We need to return the 'production' DB name to get the test DB creation
        machinery to work. This isn't a great deal in this case because DB
        names as handled by Django haven't real counterparts in Oracle.
        """
        return self.connection.settings_dict['NAME']

    def test_db_signature(self):
        settings_dict = self.connection.settings_dict
        return (
            settings_dict['HOST'],
            settings_dict['PORT'],
            settings_dict['ENGINE'],
            settings_dict['NAME'],
            self._test_database_user(),
        )
