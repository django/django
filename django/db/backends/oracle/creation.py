import sys

from django.conf import settings
from django.db import DatabaseError
from django.db.backends.base.creation import BaseDatabaseCreation
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property

TEST_DATABASE_PREFIX = "test_"


class DatabaseCreation(BaseDatabaseCreation):
    destroy_test_db_connection_close_method = "close"

    @cached_property
    def _maindb_connection(self):
        """
        This is analogous to other backends' `_nodb_connection` property,
        which allows access to an "administrative" connection which can
        be used to manage the test databases.
        For Oracle, the only connection that can be used for that purpose
        is the main (non-test) connection.
        """
        settings_dict = settings.DATABASES[self.connection.alias]
        user = settings_dict.get("SAVED_USER") or settings_dict["USER"]
        password = settings_dict.get("SAVED_PASSWORD") or settings_dict["PASSWORD"]
        settings_dict = {**settings_dict, "USER": user, "PASSWORD": password}
        DatabaseWrapper = type(self.connection)
        return DatabaseWrapper(settings_dict, alias=self.connection.alias)

    def _create_test_db(self, verbosity=1, autoclobber=False, keepdb=False):
        parameters = self._get_test_db_params()
        with self._maindb_connection.cursor() as cursor:
            if self._test_database_create():
                try:
                    self._execute_test_db_creation(
                        cursor, parameters, verbosity, keepdb
                    )
                except Exception as e:
                    if "ORA-01543" not in str(e):
                        # All errors except "tablespace already exists" cancel
                        # tests
                        self.log("Got an error creating the test database: %s" % e)
                        sys.exit(2)
                    if not autoclobber:
                        confirm = input(
                            "It appears the test database, %s, already exists. "
                            "Type 'yes' to delete it, or 'no' to cancel: "
                            % parameters["user"]
                        )
                    if autoclobber or confirm == "yes":
                        if verbosity >= 1:
                            self.log(
                                "Destroying old test database for alias '%s'..."
                                % self.connection.alias
                            )
                        try:
                            self._execute_test_db_destruction(
                                cursor, parameters, verbosity
                            )
                        except DatabaseError as e:
                            if "ORA-29857" in str(e):
                                self._handle_objects_preventing_db_destruction(
                                    cursor, parameters, verbosity, autoclobber
                                )
                            else:
                                # Ran into a database error that isn't about
                                # leftover objects in the tablespace.
                                self.log(
                                    "Got an error destroying the old test database: %s"
                                    % e
                                )
                                sys.exit(2)
                        except Exception as e:
                            self.log(
                                "Got an error destroying the old test database: %s" % e
                            )
                            sys.exit(2)
                        try:
                            self._execute_test_db_creation(
                                cursor, parameters, verbosity, keepdb
                            )
                        except Exception as e:
                            self.log(
                                "Got an error recreating the test database: %s" % e
                            )
                            sys.exit(2)
                    else:
                        self.log("Tests cancelled.")
                        sys.exit(1)

            if self._test_user_create():
                if verbosity >= 1:
                    self.log("Creating test user...")
                try:
                    self._create_test_user(cursor, parameters, verbosity, keepdb)
                except Exception as e:
                    if "ORA-01920" not in str(e):
                        # All errors except "user already exists" cancel tests
                        self.log("Got an error creating the test user: %s" % e)
                        sys.exit(2)
                    if not autoclobber:
                        confirm = input(
                            "It appears the test user, %s, already exists. Type "
                            "'yes' to delete it, or 'no' to cancel: "
                            % parameters["user"]
                        )
                    if autoclobber or confirm == "yes":
                        try:
                            if verbosity >= 1:
                                self.log("Destroying old test user...")
                            self._destroy_test_user(cursor, parameters, verbosity)
                            if verbosity >= 1:
                                self.log("Creating test user...")
                            self._create_test_user(
                                cursor, parameters, verbosity, keepdb
                            )
                        except Exception as e:
                            self.log("Got an error recreating the test user: %s" % e)
                            sys.exit(2)
                    else:
                        self.log("Tests cancelled.")
                        sys.exit(1)
        # Done with main user -- test user and tablespaces created.
        self._maindb_connection.close()
        self._switch_to_test_user(parameters)
        return self.connection.settings_dict["NAME"]

    def _switch_to_test_user(self, parameters):
        """
        Switch to the user that's used for creating the test database.

        Oracle doesn't have the concept of separate databases under the same
        user, so a separate user is used; see _create_test_db(). The main user
        is also needed for cleanup when testing is completed, so save its
        credentials in the SAVED_USER/SAVED_PASSWORD key in the settings dict.
        """
        real_settings = settings.DATABASES[self.connection.alias]
        real_settings["SAVED_USER"] = self.connection.settings_dict["SAVED_USER"] = (
            self.connection.settings_dict["USER"]
        )
        real_settings["SAVED_PASSWORD"] = self.connection.settings_dict[
            "SAVED_PASSWORD"
        ] = self.connection.settings_dict["PASSWORD"]
        real_test_settings = real_settings["TEST"]
        test_settings = self.connection.settings_dict["TEST"]
        real_test_settings["USER"] = real_settings["USER"] = test_settings["USER"] = (
            self.connection.settings_dict["USER"]
        ) = parameters["user"]
        real_settings["PASSWORD"] = self.connection.settings_dict["PASSWORD"] = (
            parameters["password"]
        )

    def set_as_test_mirror(self, primary_settings_dict):
        """
        Set this database up to be used in testing as a mirror of a primary
        database whose settings are given.
        """
        self.connection.settings_dict["USER"] = primary_settings_dict["USER"]
        self.connection.settings_dict["PASSWORD"] = primary_settings_dict["PASSWORD"]

    def _handle_objects_preventing_db_destruction(
        self, cursor, parameters, verbosity, autoclobber
    ):
        # There are objects in the test tablespace which prevent dropping it
        # The easy fix is to drop the test user -- but are we allowed to do so?
        self.log(
            "There are objects in the old test database which prevent its destruction."
            "\nIf they belong to the test user, deleting the user will allow the test "
            "database to be recreated.\n"
            "Otherwise, you will need to find and remove each of these objects, "
            "or use a different tablespace.\n"
        )
        if self._test_user_create():
            if not autoclobber:
                confirm = input("Type 'yes' to delete user %s: " % parameters["user"])
            if autoclobber or confirm == "yes":
                try:
                    if verbosity >= 1:
                        self.log("Destroying old test user...")
                    self._destroy_test_user(cursor, parameters, verbosity)
                except Exception as e:
                    self.log("Got an error destroying the test user: %s" % e)
                    sys.exit(2)
                try:
                    if verbosity >= 1:
                        self.log(
                            "Destroying old test database for alias '%s'..."
                            % self.connection.alias
                        )
                    self._execute_test_db_destruction(cursor, parameters, verbosity)
                except Exception as e:
                    self.log("Got an error destroying the test database: %s" % e)
                    sys.exit(2)
            else:
                self.log("Tests cancelled -- test database cannot be recreated.")
                sys.exit(1)
        else:
            self.log(
                "Django is configured to use pre-existing test user '%s',"
                " and will not attempt to delete it." % parameters["user"]
            )
            self.log("Tests cancelled -- test database cannot be recreated.")
            sys.exit(1)

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        """
        Create a cloned test database (tablespace + user) for parallel testing.
        """
        parameters = self._get_test_db_params(suffix)

        with self._maindb_connection.cursor() as cursor:
            if self._test_database_create():
                try:
                    self._execute_test_db_creation(
                        cursor, parameters, verbosity, keepdb
                    )
                except Exception as e:
                    if "ORA-01543" not in str(e):
                        # Errors except "tablespace exists" cancel tests
                        self.log(
                            "Got an error creating the cloned test database: %s" % e
                        )
                        sys.exit(2)
                    if not keepdb:
                        raise

            if self._test_user_create():
                try:
                    self._create_test_user(cursor, parameters, verbosity, keepdb)
                except Exception as e:
                    if "ORA-01920" not in str(e):
                        # All errors except "user already exists" cancel tests
                        self.log("Got an error creating the cloned test user: %s" % e)
                        sys.exit(2)
                    if not keepdb:
                        # Destroy and recreate if user exists and not keeping
                        self._destroy_test_user(cursor, parameters, verbosity)
                        self._create_test_user(cursor, parameters, verbosity, keepdb)

        # Run migrations on the cloned database to create tables
        if not keepdb:
            self._run_migrations_on_clone(suffix, verbosity)

    def _run_migrations_on_clone(self, suffix, verbosity):
        """
        Run migrations on the cloned database to create the schema.

        This approach avoids external dependencies like exp/imp or expdp/impdp.
        Each clone gets its own fresh migration run.
        """
        from django.apps import apps
        from django.core.management import call_command

        # Temporarily switch the connection to the cloned database
        clone_settings = self.get_test_db_clone_settings(suffix)
        original_settings = self.connection.settings_dict.copy()

        try:
            # Update connection to point to the clone
            self.connection.close()
            self.connection.settings_dict.update(clone_settings)

            # Run migrations on the clone
            if self.connection.settings_dict["TEST"].get("MIGRATE", True) is False:
                # Disable migrations for all apps
                old_migration_modules = settings.MIGRATION_MODULES
                settings.MIGRATION_MODULES = {
                    app.label: None for app in apps.get_app_configs()
                }

            try:
                call_command(
                    "migrate",
                    verbosity=max(verbosity - 1, 0),
                    interactive=False,
                    database=self.connection.alias,
                    run_syncdb=True,
                )
            finally:
                if self.connection.settings_dict["TEST"].get("MIGRATE", True) is False:
                    settings.MIGRATION_MODULES = old_migration_modules

            # Create cache table
            call_command("createcachetable", database=self.connection.alias)

        finally:
            # Restore original connection settings
            self.connection.close()
            self.connection.settings_dict.update(original_settings)

    def get_test_db_clone_settings(self, suffix):
        """
        Return a modified connection settings dict for the n-th clone of a DB.
        """
        orig = self.connection.settings_dict
        user = self._test_database_user(suffix)
        return {
            **orig,
            "USER": user,
        }

    def destroy_test_db(
        self, old_database_name=None, verbosity=1, keepdb=False, suffix=None
    ):
        """
        Destroy a test database, prompting the user for confirmation if the
        database already exists.
        """
        # Restore main user credentials for cleanup (main test db only).
        if suffix is None and not self.connection.is_pool:
            saved_user = self.connection.settings_dict.get("SAVED_USER")
            saved_password = self.connection.settings_dict.get("SAVED_PASSWORD")
            if saved_user:
                self.connection.settings_dict["USER"] = saved_user
            if saved_password:
                self.connection.settings_dict["PASSWORD"] = saved_password
        # Store suffix so _destroy_test_db can use it.
        self._suffix = suffix
        super().destroy_test_db(old_database_name, verbosity, keepdb, suffix)

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """
        Internal implementation - remove the test db tables.

        For Oracle, this drops the test user and tablespace. Uses
        self._suffix (set by destroy_test_db) to determine which
        user/tablespace to drop.
        """
        self.connection.close_pool()
        parameters = self._get_test_db_params(self._suffix)

        with self._maindb_connection.cursor() as cursor:
            if self._test_user_create():
                if verbosity >= 1:
                    self.log("Destroying test user...")
                self._destroy_test_user(cursor, parameters, verbosity)
            if self._test_database_create():
                if verbosity >= 1:
                    self.log("Destroying test database tables...")
                self._execute_test_db_destruction(cursor, parameters, verbosity)
        self._maindb_connection.close()
        self._maindb_connection.close_pool()

    def _execute_test_db_creation(self, cursor, parameters, verbosity, keepdb=False):
        if verbosity >= 2:
            self.log("_create_test_db(): dbname = %s" % parameters["user"])
        if self._test_database_oracle_managed_files():
            statements = [
                """
                CREATE TABLESPACE %(tblspace)s
                DATAFILE SIZE %(size)s
                AUTOEXTEND ON NEXT %(extsize)s MAXSIZE %(maxsize)s
                """,
                """
                CREATE TEMPORARY TABLESPACE %(tblspace_temp)s
                TEMPFILE SIZE %(size_tmp)s
                AUTOEXTEND ON NEXT %(extsize_tmp)s MAXSIZE %(maxsize_tmp)s
                """,
            ]
        else:
            statements = [
                """
                CREATE TABLESPACE %(tblspace)s
                DATAFILE '%(datafile)s' SIZE %(size)s REUSE
                AUTOEXTEND ON NEXT %(extsize)s MAXSIZE %(maxsize)s
                """,
                """
                CREATE TEMPORARY TABLESPACE %(tblspace_temp)s
                TEMPFILE '%(datafile_tmp)s' SIZE %(size_tmp)s REUSE
                AUTOEXTEND ON NEXT %(extsize_tmp)s MAXSIZE %(maxsize_tmp)s
                """,
            ]
        # Ignore "tablespace already exists" error when keepdb is on.
        acceptable_ora_err = "ORA-01543" if keepdb else None
        self._execute_allow_fail_statements(
            cursor, statements, parameters, verbosity, acceptable_ora_err
        )

    def _create_test_user(self, cursor, parameters, verbosity, keepdb=False):
        if verbosity >= 2:
            self.log("_create_test_user(): username = %s" % parameters["user"])
        statements = [
            """CREATE USER %(user)s
               IDENTIFIED BY "%(password)s"
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
        acceptable_ora_err = "ORA-01920" if keepdb else None
        success = self._execute_allow_fail_statements(
            cursor, statements, parameters, verbosity, acceptable_ora_err
        )
        # If the password was randomly generated, change the user accordingly.
        if not success and self._test_settings_get("PASSWORD") is None:
            set_password = 'ALTER USER %(user)s IDENTIFIED BY "%(password)s"'
            self._execute_statements(cursor, [set_password], parameters, verbosity)
        # Most test suites can be run without "create view" and
        # "create materialized view" privileges. But some need it.
        for object_type in ("VIEW", "MATERIALIZED VIEW"):
            extra = "GRANT CREATE %(object_type)s TO %(user)s"
            parameters["object_type"] = object_type
            success = self._execute_allow_fail_statements(
                cursor, [extra], parameters, verbosity, "ORA-01031"
            )
            if not success and verbosity >= 2:
                self.log(
                    "Failed to grant CREATE %s permission to test user. This may be ok."
                    % object_type
                )

    def _execute_test_db_destruction(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            self.log("_execute_test_db_destruction(): dbname=%s" % parameters["user"])
        statements = [
            "DROP TABLESPACE %(tblspace)s "
            "INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS",
            "DROP TABLESPACE %(tblspace_temp)s "
            "INCLUDING CONTENTS AND DATAFILES CASCADE CONSTRAINTS",
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _destroy_test_user(self, cursor, parameters, verbosity):
        if verbosity >= 2:
            self.log("_destroy_test_user(): user=%s" % parameters["user"])
            self.log("Be patient. This can take some time...")
        statements = [
            "DROP USER %(user)s CASCADE",
        ]
        self._execute_statements(cursor, statements, parameters, verbosity)

    def _execute_statements(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        for template in statements:
            stmt = template % parameters
            if verbosity >= 2:
                print(stmt)
            try:
                cursor.execute(stmt)
            except Exception as err:
                if (not allow_quiet_fail) or verbosity >= 2:
                    self.log("Failed (%s)" % (err))
                raise

    def _execute_allow_fail_statements(
        self, cursor, statements, parameters, verbosity, acceptable_ora_err
    ):
        """
        Execute statements which are allowed to fail silently if the Oracle
        error code given by `acceptable_ora_err` is raised. Return True if the
        statements execute without an exception, or False otherwise.
        """
        try:
            # Statement can fail when acceptable_ora_err is not None
            allow_quiet_fail = (
                acceptable_ora_err is not None and len(acceptable_ora_err) > 0
            )
            self._execute_statements(
                cursor,
                statements,
                parameters,
                verbosity,
                allow_quiet_fail=allow_quiet_fail,
            )
            return True
        except DatabaseError as err:
            description = str(err)
            if acceptable_ora_err is None or acceptable_ora_err not in description:
                raise
            return False

    def _get_test_db_params(self, suffix=None):
        return {
            "dbname": self._test_database_name(),
            "user": self._test_database_user(suffix),
            "password": (
                self.connection.settings_dict["PASSWORD"]
                if suffix
                else self._test_database_passwd()
            ),
            "tblspace": self._test_database_tblspace(suffix),
            "tblspace_temp": self._test_database_tblspace_tmp(suffix),
            "datafile": self._test_database_tblspace_datafile(suffix),
            "datafile_tmp": self._test_database_tblspace_tmp_datafile(suffix),
            "maxsize": self._test_database_tblspace_maxsize(),
            "maxsize_tmp": self._test_database_tblspace_tmp_maxsize(),
            "size": self._test_database_tblspace_size(),
            "size_tmp": self._test_database_tblspace_tmp_size(),
            "extsize": self._test_database_tblspace_extsize(),
            "extsize_tmp": self._test_database_tblspace_tmp_extsize(),
        }

    def _test_settings_get(self, key, default=None, prefixed=None):
        """
        Return a value from the test settings dict, or a given default, or a
        prefixed entry from the main settings dict.
        """
        settings_dict = self.connection.settings_dict
        val = settings_dict["TEST"].get(key, default)
        if val is None and prefixed:
            val = TEST_DATABASE_PREFIX + settings_dict[prefixed]
        return val

    def _test_database_name(self):
        return self._test_settings_get("NAME", prefixed="NAME")

    def _test_database_create(self):
        return self._test_settings_get("CREATE_DB", default=True)

    def _test_user_create(self):
        return self._test_settings_get("CREATE_USER", default=True)

    def _test_database_user(self, suffix=None):
        user = self._test_settings_get("USER", prefixed="USER")
        if suffix:
            user = f"{user}_{suffix}"
        return user

    def _test_database_passwd(self):
        password = self._test_settings_get("PASSWORD")
        if password is None and self._test_user_create():
            # Oracle passwords are limited to 30 chars and can't contain
            # symbols.
            password = get_random_string(30)
        return password

    def _test_database_tblspace(self, suffix=None):
        tblspace = self._test_settings_get("TBLSPACE", prefixed="USER")
        if suffix:
            tblspace = f"{tblspace}_{suffix}"
        return tblspace

    def _test_database_tblspace_tmp(self, suffix=None):
        settings_dict = self.connection.settings_dict
        tblspace_tmp = settings_dict["TEST"].get(
            "TBLSPACE_TMP", TEST_DATABASE_PREFIX + settings_dict["USER"] + "_temp"
        )
        if suffix:
            tblspace_tmp = f"{tblspace_tmp}_{suffix}"
        return tblspace_tmp

    def _test_database_tblspace_datafile(self, suffix=None):
        default = "%s.dbf" % self._test_database_tblspace(suffix)
        datafile = self._test_settings_get("DATAFILE", default=default)
        if suffix and datafile != default:
            path, ext = datafile.rsplit(".", 1)
            datafile = f"{path}_{suffix}.{ext}"
        return datafile

    def _test_database_tblspace_tmp_datafile(self, suffix=None):
        default = "%s.dbf" % self._test_database_tblspace_tmp(suffix)
        datafile = self._test_settings_get("DATAFILE_TMP", default=default)
        if suffix and datafile != default:
            path, ext = datafile.rsplit(".", 1)
            datafile = f"{path}_{suffix}.{ext}"
        return datafile

    def _test_database_tblspace_maxsize(self):
        return self._test_settings_get("DATAFILE_MAXSIZE", default="500M")

    def _test_database_tblspace_tmp_maxsize(self):
        return self._test_settings_get("DATAFILE_TMP_MAXSIZE", default="500M")

    def _test_database_tblspace_size(self):
        return self._test_settings_get("DATAFILE_SIZE", default="50M")

    def _test_database_tblspace_tmp_size(self):
        return self._test_settings_get("DATAFILE_TMP_SIZE", default="50M")

    def _test_database_tblspace_extsize(self):
        return self._test_settings_get("DATAFILE_EXTSIZE", default="25M")

    def _test_database_tblspace_tmp_extsize(self):
        return self._test_settings_get("DATAFILE_TMP_EXTSIZE", default="25M")

    def _test_database_oracle_managed_files(self):
        return self._test_settings_get("ORACLE_MANAGED_FILES", default=False)

    def _get_test_db_name(self):
        """
        Return the 'production' DB name to get the test DB creation machinery
        to work. This isn't a great deal in this case because DB names as
        handled by Django don't have real counterparts in Oracle.
        """
        return self.connection.settings_dict["NAME"]

    def test_db_signature(self):
        settings_dict = self.connection.settings_dict
        return (
            settings_dict["HOST"],
            settings_dict["PORT"],
            settings_dict["ENGINE"],
            settings_dict["NAME"],
            self._test_database_user(),
        )
