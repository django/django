import sys
import time

from django.conf import settings
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.utils import DatabaseError
from django.utils.six.moves import input

TEST_DATABASE_PREFIX = 'test_'
PASSWORD = 'Im_a_lumberjack'


class DatabaseCreation(BaseDatabaseCreation):

    def _create_test_db(self, verbosity=1, autoclobber=False, keepdb=False):
        parameters = self._get_test_db_params()
        cursor = self.connection.cursor()
        if self._test_database_create():
            try:
                self._execute_test_db_creation(cursor, parameters, verbosity, keepdb)
            except Exception as e:
                # if we want to keep the db, then no need to do any of the below,
                # just return and skip it all.
                if keepdb:
                    return
                sys.stderr.write("Got an error creating the test database: %s\n" % e)
                if not autoclobber:
                    confirm = input(
                        "It appears the test database, %s, already exists. "
                        "Type 'yes' to delete it, or 'no' to cancel: " % parameters['user'])
                if autoclobber or confirm == 'yes':
                    if verbosity >= 1:
                        print("Destroying old test database '%s'..." % self.connection.alias)
                    try:
                        self._execute_test_db_destruction(cursor, parameters, verbosity)
                    except DatabaseError as e:
                        if 'ORA-29857' in str(e):
                            self._handle_objects_preventing_db_destruction(cursor, parameters,
                                                                           verbosity, autoclobber)
                        else:
                            # Ran into a database error that isn't about leftover objects in the tablespace
                            sys.stderr.write("Got an error destroying the old test database: %s\n" % e)
                            sys.exit(2)
                    except Exception as e:
                        sys.stderr.write("Got an error destroying the old test database: %s\n" % e)
                        sys.exit(2)
                    try:
                        self._execute_test_db_creation(cursor, parameters, verbosity, keepdb)
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
                self._create_test_user(cursor, parameters, verbosity, keepdb)
            except Exception as e:
                # If we want to keep the db, then we want to also keep the user.
                if keepdb:
                    return
                sys.stderr.write("Got an error creating the test user: %s\n" % e)
                if not autoclobber:
                    confirm = input(
                        "It appears the test user, %s, already exists. Type "
                        "'yes' to delete it, or 'no' to cancel: " % parameters['user'])
                if autoclobber or confirm == 'yes':
                    try:
                        if verbosity >= 1:
                            print("Destroying old test user...")
                        self._destroy_test_user(cursor, parameters, verbosity)
                        if verbosity >= 1:
                            print("Creating test user...")
                        self._create_test_user(cursor, parameters, verbosity, keepdb)
                    except Exception as e:
                        sys.stderr.write("Got an error recreating the test user: %s\n" % e)
                        sys.exit(2)
                else:
                    print("Tests cancelled.")
                    sys.exit(1)

        self.connection.close()  # done with main user -- test user and tablespaces created

        real_settings = settings.DATABASES[self.connection.alias]
        real_settings['SAVED_USER'] = self.connection.settings_dict['SAVED_USER'] = \
            self.connection.settings_dict['USER']
        real_settings['SAVED_PASSWORD'] = self.connection.settings_dict['SAVED_PASSWORD'] = \
            self.connection.settings_dict['PASSWORD']
        real_test_settings = real_settings['TEST']
        test_settings = self.connection.settings_dict['TEST']
        real_test_settings['USER'] = real_settings['USER'] = test_settings['USER'] = \
            self.connection.settings_dict['USER'] = parameters['user']
        real_settings['PASSWORD'] = self.connection.settings_dict['PASSWORD'] = parameters['password']

        return self.connection.settings_dict['NAME']

    def _handle_objects_preventing_db_destruction(self, cursor, parameters, verbosity, autoclobber):
        # There are objects in the test tablespace which prevent dropping it
        # The easy fix is to drop the test user -- but are we allowed to do so?
        print("There are objects in the old test database which prevent its destruction.")
        print("If they belong to the test user, deleting the user will allow the test "
              "database to be recreated.")
        print("Otherwise, you will need to find and remove each of these objects, "
              "or use a different tablespace.\n")
        if self._test_user_create():
            if not autoclobber:
                confirm = input("Type 'yes' to delete user %s: " % parameters['user'])
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print("Destroying old test user...")
                    self._destroy_test_user(cursor, parameters, verbosity)
                except Exception as e:
                    sys.stderr.write("Got an error destroying the test user: %s\n" % e)
                    sys.exit(2)
                try:
                    if verbosity >= 1:
                        print("Destroying old test database '%s'..." % self.connection.alias)
                    self._execute_test_db_destruction(cursor, parameters, verbosity)
                except Exception as e:
                    sys.stderr.write("Got an error destroying the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print("Tests cancelled -- test database cannot be recreated.")
                sys.exit(1)
        else:
            print("Django is configured to use pre-existing test user '%s',"
                  " and will not attempt to delete it.\n" % parameters['user'])
            print("Tests cancelled -- test database cannot be recreated.")
            sys.exit(1)

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists. Returns the name of the test database created.
        """
        self.connection.settings_dict['USER'] = self.connection.settings_dict['SAVED_USER']
        self.connection.settings_dict['PASSWORD'] = self.connection.settings_dict['SAVED_PASSWORD']
        parameters = self._get_test_db_params()
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

    def _execute_test_db_creation(self, cursor, parameters, verbosity, keepdb=False):
        if verbosity >= 2:
            print("_create_test_db(): dbname = %s" % parameters['user'])
        statements = [
            """CREATE TABLESPACE %(tblspace)s
               DATAFILE '%(datafile)s' SIZE 20M
               REUSE AUTOEXTEND ON NEXT 10M MAXSIZE %(maxsize)s
            """,
            """CREATE TEMPORARY TABLESPACE %(tblspace_temp)s
               TEMPFILE '%(datafile_tmp)s' SIZE 20M
               REUSE AUTOEXTEND ON NEXT 10M MAXSIZE %(maxsize_tmp)s
            """,
        ]
        # Ignore "tablespace already exists" error when keepdb is on.
        acceptable_ora_err = 'ORA-01543' if keepdb else None
        self._execute_allow_fail_statements(cursor, statements, parameters, verbosity, acceptable_ora_err)

    def _create_test_user(self, cursor, parameters, verbosity, keepdb=False):
        if verbosity >= 2:
            print("_create_test_user(): username = %s" % parameters['user'])
        statements = [
            """CREATE USER %(user)s
               IDENTIFIED BY %(password)s
               DEFAULT TABLESPACE %(tblspace)s
               TEMPORARY TABLESPACE %(tblspace_temp)s
               QUOTA UNLIMITED ON %(tblspace)s
            """,
            """GRANT CREATE SESSION,
                     CREATE TABLE,
                     CREATE SEQUENCE,
                     CREATE PROCEDURE,
                     CREATE TRIGGER
               TO %(user)s""",
        ]
        # Ignore "user already exists" error when keepdb is on
        acceptable_ora_err = 'ORA-01920' if keepdb else None
        self._execute_allow_fail_statements(cursor, statements, parameters, verbosity, acceptable_ora_err)
        # Most test-suites can be run without the create-view privilege. But some need it.
        extra = "GRANT CREATE VIEW TO %(user)s"
        success = self._execute_allow_fail_statements(cursor, [extra], parameters, verbosity, 'ORA-01031')
        if not success and verbosity >= 2:
            print("Failed to grant CREATE VIEW permission to test user. This may be ok.")

    def _execute_test_db_destruction(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            print("_execute_test_db_destruction(): dbname=%s" % parameters['user'])
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

    def _execute_statements(self, cursor, statements, parameters, verbosity, allow_quiet_fail=False):
        for template in statements:
            stmt = template % parameters
            if verbosity >= 2:
                print(stmt)
            try:
                cursor.execute(stmt)
            except Exception as err:
                if (not allow_quiet_fail) or verbosity >= 2:
                    sys.stderr.write("Failed (%s)\n" % (err))
                raise

    def _execute_allow_fail_statements(self, cursor, statements, parameters, verbosity, acceptable_ora_err):
        """
        Execute statements which are allowed to fail silently if the Oracle
        error code given by `acceptable_ora_err` is raised. Return True if the
        statements execute without an exception, or False otherwise.
        """
        try:
            # Statement can fail when acceptable_ora_err is not None
            allow_quiet_fail = acceptable_ora_err is not None and len(acceptable_ora_err) > 0
            self._execute_statements(cursor, statements, parameters, verbosity, allow_quiet_fail=allow_quiet_fail)
            return True
        except DatabaseError as err:
            description = str(err)
            if acceptable_ora_err is None or acceptable_ora_err not in description:
                raise
            return False

    def _get_test_db_params(self):
        return {
            'dbname': self._test_database_name(),
            'user': self._test_database_user(),
            'password': self._test_database_passwd(),
            'tblspace': self._test_database_tblspace(),
            'tblspace_temp': self._test_database_tblspace_tmp(),
            'datafile': self._test_database_tblspace_datafile(),
            'datafile_tmp': self._test_database_tblspace_tmp_datafile(),
            'maxsize': self._test_database_tblspace_size(),
            'maxsize_tmp': self._test_database_tblspace_tmp_size(),
        }

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
        return self._test_settings_get('TBLSPACE', prefixed='USER')

    def _test_database_tblspace_tmp(self):
        settings_dict = self.connection.settings_dict
        return settings_dict['TEST'].get('TBLSPACE_TMP',
                                         TEST_DATABASE_PREFIX + settings_dict['USER'] + '_temp')

    def _test_database_tblspace_datafile(self):
        tblspace = '%s.dbf' % self._test_database_tblspace()
        return self._test_settings_get('DATAFILE', default=tblspace)

    def _test_database_tblspace_tmp_datafile(self):
        tblspace = '%s.dbf' % self._test_database_tblspace_tmp()
        return self._test_settings_get('DATAFILE_TMP', default=tblspace)

    def _test_database_tblspace_size(self):
        return self._test_settings_get('DATAFILE_MAXSIZE', default='500M')

    def _test_database_tblspace_tmp_size(self):
        return self._test_settings_get('DATAFILE_TMP_MAXSIZE', default='500M')

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
