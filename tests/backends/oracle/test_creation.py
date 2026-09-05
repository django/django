import unittest
from io import StringIO
from unittest import mock

from django.db import DatabaseError, connection
from django.db.backends.oracle.creation import DatabaseCreation
from django.test import TestCase


@unittest.skipUnless(connection.vendor == "oracle", "Oracle tests")
@mock.patch.object(DatabaseCreation, "_maindb_connection", return_value=connection)
@mock.patch("sys.stdout", new_callable=StringIO)
@mock.patch("sys.stderr", new_callable=StringIO)
class DatabaseCreationTests(TestCase):
    def _execute_raise_user_already_exists(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        # Raise "user already exists" only in test user creation
        if statements and statements[0].startswith("CREATE USER"):
            raise DatabaseError(
                "ORA-01920: user name 'string' conflicts with another user or role name"
            )

    def _execute_raise_tablespace_already_exists(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        raise DatabaseError("ORA-01543: tablespace 'string' already exists")

    def _execute_raise_insufficient_privileges(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        raise DatabaseError("ORA-01031: insufficient privileges")

    def _make_execute_record_and_raise_tablespace_exists(self, executed):
        # Record executed statements and raise "tablespace exists" the first
        # time a tablespace is created, as a leftover clone would.
        state = {"raised": False}

        def execute(inner_self, cursor, statements, parameters, verbosity, **kwargs):
            for statement in statements:
                executed.append(statement.strip())
                if (
                    statement.strip().startswith("CREATE TABLESPACE")
                    and not state["raised"]
                ):
                    state["raised"] = True
                    raise DatabaseError("ORA-01543: tablespace 'string' already exists")

        return execute

    def _test_database_passwd(self):
        # Mocked to avoid test user password changed
        return connection.settings_dict["SAVED_PASSWORD"]

    def patch_execute_statements(self, execute_statements):
        return mock.patch.object(
            DatabaseCreation, "_execute_statements", execute_statements
        )

    @mock.patch.object(DatabaseCreation, "_test_user_create", return_value=False)
    def test_create_test_db(self, *mocked_objects):
        creation = DatabaseCreation(connection)
        # Simulate test database creation raising "tablespace already exists"
        with self.patch_execute_statements(
            self._execute_raise_tablespace_already_exists
        ):
            with mock.patch("builtins.input", return_value="no"):
                with self.assertRaises(SystemExit):
                    # SystemExit is raised if the user answers "no" to the
                    # prompt asking if it's okay to delete the test tablespace.
                    creation._create_test_db(verbosity=0, keepdb=False)
            # "Tablespace already exists" error is ignored when keepdb is on
            creation._create_test_db(verbosity=0, keepdb=True)
        # Simulate test database creation raising unexpected error
        with self.patch_execute_statements(self._execute_raise_insufficient_privileges):
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, keepdb=False)
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, keepdb=True)

    @mock.patch.object(DatabaseCreation, "_test_database_create", return_value=False)
    def test_create_test_user(self, *mocked_objects):
        creation = DatabaseCreation(connection)
        with mock.patch.object(
            DatabaseCreation, "_test_database_passwd", self._test_database_passwd
        ):
            # Simulate test user creation raising "user already exists"
            with self.patch_execute_statements(self._execute_raise_user_already_exists):
                with mock.patch("builtins.input", return_value="no"):
                    with self.assertRaises(SystemExit):
                        # SystemExit is raised if the user answers "no" to the
                        # prompt asking if it's okay to delete the test user.
                        creation._create_test_db(verbosity=0, keepdb=False)
                # "User already exists" error is ignored when keepdb is on
                creation._create_test_db(verbosity=0, keepdb=True)
            # Simulate test user creation raising unexpected error
            with self.patch_execute_statements(
                self._execute_raise_insufficient_privileges
            ):
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, keepdb=False)
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, keepdb=True)

    def test_oracle_managed_files(self, *mocked_objects):
        def _execute_capture_statements(
            self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
        ):
            self.tblspace_sqls = statements

        creation = DatabaseCreation(connection)
        # Simulate test database creation with Oracle Managed File (OMF)
        # tablespaces.
        with mock.patch.object(
            DatabaseCreation, "_test_database_oracle_managed_files", return_value=True
        ):
            with self.patch_execute_statements(_execute_capture_statements):
                with connection.cursor() as cursor:
                    creation._execute_test_db_creation(
                        cursor, creation._get_test_db_params(), verbosity=0
                    )
                    tblspace_sql, tblspace_tmp_sql = creation.tblspace_sqls
                    # Datafile names shouldn't appear.
                    self.assertIn("DATAFILE SIZE", tblspace_sql)
                    self.assertIn("TEMPFILE SIZE", tblspace_tmp_sql)
                    # REUSE cannot be used with OMF.
                    self.assertNotIn("REUSE", tblspace_sql)
                    self.assertNotIn("REUSE", tblspace_tmp_sql)

    def test_get_test_db_params_suffix(self, *mocked_objects):
        """Test that _get_test_db_params generates correct suffixed names."""
        creation = DatabaseCreation(connection)
        # Without suffix
        params = creation._get_test_db_params()
        base_user = params["user"]
        base_tblspace = params["tblspace"]
        base_tblspace_temp = params["tblspace_temp"]

        # With suffix
        params_suffixed = creation._get_test_db_params("1")
        self.assertEqual(params_suffixed["user"], f"{base_user}_1")
        self.assertEqual(params_suffixed["tblspace"], f"{base_tblspace}_1")
        self.assertEqual(params_suffixed["tblspace_temp"], f"{base_tblspace_temp}_1")
        # dbname should not change (Oracle SID/service name stays same)
        self.assertEqual(params_suffixed["dbname"], params["dbname"])

    def test_get_test_db_clone_settings(self, *mocked_objects):
        """Test that get_test_db_clone_settings returns correct settings."""
        creation = DatabaseCreation(connection)
        orig_test_user = connection.settings_dict["TEST"].get("USER")

        clone_settings = creation.get_test_db_clone_settings("2")
        # USER should be suffixed
        expected_user = creation._test_database_user("2")
        self.assertEqual(clone_settings["USER"], expected_user)
        # TEST["USER"] follows USER, otherwise _test_database_user() reports
        # the main test user inside a parallel worker.
        self.assertEqual(clone_settings["TEST"]["USER"], expected_user)
        # NAME should remain unchanged (Oracle SID doesn't change)
        self.assertEqual(clone_settings["NAME"], connection.settings_dict["NAME"])
        # The connection's own settings are left alone.
        self.assertEqual(connection.settings_dict["TEST"].get("USER"), orig_test_user)

    def test_datafile_suffix_no_extension(self, *mocked_objects):
        """A custom DATAFILE without an extension is suffixed, not crashed."""
        creation = DatabaseCreation(connection)
        # Bare name, no dot -- previously raised ValueError on rsplit(".", 1).
        self.assertEqual(
            creation._insert_datafile_suffix("/u01/oradata/clone", "1"),
            "/u01/oradata/clone_1",
        )
        # Normal case: suffix goes before the extension.
        self.assertEqual(
            creation._insert_datafile_suffix("/u01/oradata/clone.dbf", "2"),
            "/u01/oradata/clone_2.dbf",
        )

    @mock.patch.object(DatabaseCreation, "_run_migrations_on_clone")
    @mock.patch.object(DatabaseCreation, "_test_user_create", return_value=False)
    def test_clone_test_db_tablespace_exists_keepdb(
        self, mocked_test_user_create, mocked_run_migrations, *mocked_objects
    ):
        """
        With keepdb, a pre-existing clone tablespace is reused rather than
        recreated, but the clone is still migrated: it may have just been
        created, and migrate() is a no-op on one that's already built.
        """
        creation = DatabaseCreation(connection)
        # Simulate tablespace already exists error
        with self.patch_execute_statements(
            self._execute_raise_tablespace_already_exists
        ):
            # Should not raise when keepdb=True
            creation._clone_test_db(suffix="1", verbosity=0, keepdb=True)
        mocked_run_migrations.assert_called_once_with("1", 0)

    @mock.patch.object(DatabaseCreation, "_run_migrations_on_clone")
    @mock.patch.object(DatabaseCreation, "_test_user_create", return_value=False)
    def test_clone_test_db_recreates_existing_tablespace(self, *mocked_objects):
        """
        Without keepdb, a clone tablespace left over from an earlier
        interrupted run is dropped and recreated rather than aborting the run.
        """
        creation = DatabaseCreation(connection)
        executed = []
        execute = self._make_execute_record_and_raise_tablespace_exists(executed)
        with self.patch_execute_statements(execute):
            # Should recover instead of raising.
            creation._clone_test_db(suffix="1", verbosity=0, keepdb=False)
        # The leftover user and tablespace are dropped before recreating.
        self.assertTrue(any(s.startswith("DROP USER") for s in executed))
        self.assertTrue(any(s.startswith("DROP TABLESPACE") for s in executed))

    @mock.patch.object(DatabaseCreation, "_test_user_create", return_value=False)
    def test_clone_test_db_unexpected_error(self, *mocked_objects):
        """Test that _clone_test_db exits on unexpected errors."""
        creation = DatabaseCreation(connection)
        with self.patch_execute_statements(self._execute_raise_insufficient_privileges):
            with self.assertRaises(SystemExit):
                creation._clone_test_db(suffix="1", verbosity=0, keepdb=False)
            with self.assertRaises(SystemExit):
                creation._clone_test_db(suffix="1", verbosity=0, keepdb=True)

    @mock.patch("django.db.backends.oracle.creation.time.sleep")
    def test_destroy_test_user_waits_for_lingering_session(self, *mocked_objects):
        """
        A departed parallel worker's Oracle session can outlive its process, so
        DROP USER is retried for as long as it reports ORA-01940.
        """
        creation = DatabaseCreation(connection)
        attempts = []

        def execute(inner_self, cursor, statements, parameters, verbosity, **kwargs):
            attempts.append(statements[0])
            if len(attempts) < 3:
                raise DatabaseError(
                    "ORA-01940: cannot drop a user who is currently connected"
                )

        with self.patch_execute_statements(execute):
            creation._destroy_test_user(None, {"user": "default_test_1"}, 0)
        self.assertEqual(len(attempts), 3)

    @mock.patch("django.db.backends.oracle.creation.time.sleep")
    def test_destroy_test_user_gives_up_on_lingering_session(self, *mocked_objects):
        """DROP USER still raises if the session never goes away."""
        creation = DatabaseCreation(connection)
        creation.destroy_test_user_timeout = 0

        def execute(inner_self, cursor, statements, parameters, verbosity, **kwargs):
            raise DatabaseError(
                "ORA-01940: cannot drop a user who is currently connected"
            )

        with self.patch_execute_statements(execute):
            with self.assertRaises(DatabaseError):
                creation._destroy_test_user(None, {"user": "default_test_1"}, 0)
