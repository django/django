import subprocess
import unittest
from io import BytesIO, StringIO
from unittest import mock

from django.db import DatabaseError, connection
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.mysql.creation import DatabaseCreation
from django.test import SimpleTestCase
from django.test.utils import captured_stderr


@unittest.skipUnless(connection.vendor == "mysql", "MySQL tests")
class DatabaseCreationTests(SimpleTestCase):
    def _execute_raise_database_exists(self, cursor, parameters, keepdb=False):
        raise DatabaseError(
            1007, "Can't create database '%s'; database exists" % parameters["dbname"]
        )

    def _execute_raise_access_denied(self, cursor, parameters, keepdb=False):
        raise DatabaseError(1044, "Access denied for user")

    def patch_test_db_creation(self, execute_create_test_db):
        return mock.patch.object(
            BaseDatabaseCreation, "_execute_create_test_db", execute_create_test_db
        )

    @mock.patch("sys.stdout", new_callable=StringIO)
    @mock.patch("sys.stderr", new_callable=StringIO)
    def test_create_test_db_database_exists(self, *mocked_objects):
        # Simulate test database creation raising "database exists"
        creation = DatabaseCreation(connection)
        with self.patch_test_db_creation(self._execute_raise_database_exists):
            with mock.patch("builtins.input", return_value="no"):
                with self.assertRaises(SystemExit):
                    # SystemExit is raised if the user answers "no" to the
                    # prompt asking if it's okay to delete the test database.
                    creation._create_test_db(
                        verbosity=0, autoclobber=False, keepdb=False
                    )
            # "Database exists" shouldn't appear when keepdb is on
            creation._create_test_db(verbosity=0, autoclobber=False, keepdb=True)

    @mock.patch("sys.stdout", new_callable=StringIO)
    @mock.patch("sys.stderr", new_callable=StringIO)
    def test_create_test_db_unexpected_error(self, *mocked_objects):
        # Simulate test database creation raising unexpected error
        creation = DatabaseCreation(connection)
        with self.patch_test_db_creation(self._execute_raise_access_denied):
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, autoclobber=False, keepdb=False)

    def test_clone_test_db_database_exists(self):
        creation = DatabaseCreation(connection)
        with self.patch_test_db_creation(self._execute_raise_database_exists):
            with mock.patch.object(DatabaseCreation, "_clone_db") as _clone_db:
                creation._clone_test_db("suffix", verbosity=0, keepdb=True)
                _clone_db.assert_not_called()

    def test_clone_test_db_options_ordering(self):
        creation = DatabaseCreation(connection)
        mock_subprocess_call = mock.MagicMock()
        mock_subprocess_call.returncode = 0
        try:
            saved_settings = connection.settings_dict
            connection.settings_dict = {
                "NAME": "source_db",
                "USER": "",
                "PASSWORD": "",
                "PORT": "",
                "HOST": "",
                "ENGINE": "django.db.backends.mysql",
                "OPTIONS": {
                    "read_default_file": "my.cnf",
                },
            }
            with mock.patch.object(subprocess, "Popen") as mocked_popen:
                mocked_popen.return_value.__enter__.return_value = mock_subprocess_call
                creation._clone_db("source_db", "target_db")
                mocked_popen.assert_has_calls(
                    [
                        mock.call(
                            [
                                "mysqldump",
                                "--defaults-file=my.cnf",
                                "--routines",
                                "--events",
                                "source_db",
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env=None,
                        ),
                    ]
                )
        finally:
            connection.settings_dict = saved_settings

    def test_clone_test_db_subprocess_mysqldump_error(self):
        creation = DatabaseCreation(connection)
        mock_subprocess_call = mock.MagicMock()
        mock_subprocess_call.returncode = 0
        # Simulate mysqldump in test database cloning raises an error.
        msg = "Couldn't execute 'SELECT ...'"
        mock_subprocess_call_error = mock.MagicMock()
        mock_subprocess_call_error.returncode = 2
        mock_subprocess_call_error.stderr = BytesIO(msg.encode())
        with mock.patch.object(subprocess, "Popen") as mocked_popen:
            mocked_popen.return_value.__enter__.side_effect = [
                mock_subprocess_call_error,  # mysqldump mock
                mock_subprocess_call,  # load mock
            ]
            with captured_stderr() as err, self.assertRaises(SystemExit) as cm:
                creation._clone_db("source_db", "target_db")
            self.assertEqual(cm.exception.code, 2)
        self.assertIn(
            f"Got an error on mysqldump when cloning the test database: {msg}",
            err.getvalue(),
        )

    def test_clone_test_db_subprocess_mysql_error(self):
        creation = DatabaseCreation(connection)
        mock_subprocess_call = mock.MagicMock()
        mock_subprocess_call.returncode = 0
        # Simulate load in test database cloning raises an error.
        msg = "Some error"
        mock_subprocess_call_error = mock.MagicMock()
        mock_subprocess_call_error.returncode = 3
        mock_subprocess_call_error.stderr = BytesIO(msg.encode())
        with mock.patch.object(subprocess, "Popen") as mocked_popen:
            mocked_popen.return_value.__enter__.side_effect = [
                mock_subprocess_call,  # mysqldump mock
                mock_subprocess_call_error,  # load mock
            ]
            with captured_stderr() as err, self.assertRaises(SystemExit) as cm:
                creation._clone_db("source_db", "target_db")
            self.assertEqual(cm.exception.code, 3)
        self.assertIn(f"Got an error cloning the test database: {msg}", err.getvalue())
