import copy
import multiprocessing
import sqlite3
import unittest
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, NotSupportedError, connection, connections
from django.test import SimpleTestCase


@unittest.skipUnless(connection.vendor == "sqlite", "SQLite tests")
class TestDbSignatureTests(SimpleTestCase):
    def test_custom_test_name(self):
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.deepcopy(
            connections[DEFAULT_DB_ALIAS].settings_dict
        )
        test_connection.settings_dict["NAME"] = None
        test_connection.settings_dict["TEST"]["NAME"] = "custom.sqlite.db"
        signature = test_connection.creation_class(test_connection).test_db_signature()
        self.assertEqual(signature, (None, "custom.sqlite.db"))

    def test_get_test_db_clone_settings_name(self):
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.deepcopy(
            connections[DEFAULT_DB_ALIAS].settings_dict,
        )
        tests = [
            ("test.sqlite3", "test_1.sqlite3"),
            ("test", "test_1"),
        ]
        for test_db_name, expected_clone_name in tests:
            with self.subTest(test_db_name=test_db_name):
                test_connection.settings_dict["NAME"] = test_db_name
                test_connection.settings_dict["TEST"]["NAME"] = test_db_name
                creation_class = test_connection.creation_class(test_connection)
                clone_settings_dict = creation_class.get_test_db_clone_settings("1")
                self.assertEqual(clone_settings_dict["NAME"], expected_clone_name)

    @mock.patch.object(multiprocessing, "get_start_method", return_value="unsupported")
    def test_get_test_db_clone_settings_not_supported(self, *mocked_objects):
        msg = "Cloning with start method 'unsupported' is not supported."
        with self.assertRaisesMessage(NotSupportedError, msg):
            connection.creation.get_test_db_clone_settings(1)

    @mock.patch.object(multiprocessing, "get_start_method", return_value="spawn")
    def test_setup_worker_connection_respects_test_database_name(self, *mocked_objects):
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.deepcopy(
            connections[DEFAULT_DB_ALIAS].settings_dict
        )
        tests = [
            ("mytest.db", "mytest_2.db"),
            ("mytest", "mytest_2"),
        ]
        for test_db_name, expected_source_db_name in tests:
            with self.subTest(test_db_name=test_db_name):
                # When calling setup_worker_connection(), the test db has been
                # created already and its name has been copied to
                # settings_dict["NAME"], so no need to set ["TEST"]["NAME"].
                test_connection.settings_dict["NAME"] = test_db_name
                creation_class = test_connection.creation_class(test_connection)
                worker_id = 2
                mock_source_db = mock.MagicMock()
                mock_target_db = mock.MagicMock()
                with (
                    # Mock connection to source test database.
                    mock.patch.object(
                        test_connection.Database,
                        "connect",
                        return_value=mock_source_db,
                    ) as mock_source_connect,
                    # Mock connection to target in-memory db for copying.
                    mock.patch.object(
                        sqlite3,
                        "connect",
                        return_value=mock_target_db,
                    ) as mock_target_connect,
                    # Mock reconnection to target in-memory db after copying.
                    mock.patch.object(test_connection, "connect"),
                ):
                    creation_class.setup_worker_connection(worker_id)
                mock_source_connect.assert_called_once_with(
                    f"file:{expected_source_db_name}?mode=ro",
                    uri=True,
                )
                mock_target_connect.assert_called_once_with(
                    "file:memorydb_default_2?mode=memory&cache=shared",
                    uri=True,
                )
                mock_source_db.backup.assert_called_once_with(mock_target_db)
                mock_source_db.close.assert_called_once()
                mock_target_db.close.assert_called_once()
