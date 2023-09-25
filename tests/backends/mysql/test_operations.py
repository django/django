import unittest
from unittest import mock

from django.core.management.color import no_style
from django.db import connection
from django.db.backends.mysql.operations import DatabaseOperations
from django.test import SimpleTestCase

from ..models import Person, Tag


@unittest.skipUnless(connection.vendor == "mysql", "MySQL tests.")
class MySQLOperationsTests(SimpleTestCase):
    def test_sql_flush(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                self.assertEqual(
                    connection.ops.sql_flush(
                        no_style(),
                        [Person._meta.db_table, Tag._meta.db_table],
                        allow_cascade=allow_cascade,
                    ),
                    [
                        "SET FOREIGN_KEY_CHECKS = 0;",
                        "DELETE FROM `backends_person`;",
                        "DELETE FROM `backends_tag`;",
                        "SET FOREIGN_KEY_CHECKS = 1;",
                    ],
                )

    def test_sql_flush_sequences(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                self.assertEqual(
                    connection.ops.sql_flush(
                        no_style(),
                        [Person._meta.db_table, Tag._meta.db_table],
                        reset_sequences=True,
                        allow_cascade=allow_cascade,
                    ),
                    [
                        "SET FOREIGN_KEY_CHECKS = 0;",
                        "TRUNCATE `backends_person`;",
                        "TRUNCATE `backends_tag`;",
                        "SET FOREIGN_KEY_CHECKS = 1;",
                    ],
                )

    def test_for_share_sql(self):
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (8, 0, 1)
            _connection.mysql_is_mariadb = False
            operations = DatabaseOperations(_connection)
            self.assertEqual(operations.for_share_sql(), "FOR SHARE")
            self.assertEqual(operations.for_share_sql(nowait=True), "FOR SHARE NOWAIT")
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (8, 0, 0)
            _connection.mysql_is_mariadb = False
            operations = DatabaseOperations(_connection)
            self.assertEqual(operations.for_share_sql(), "LOCK IN SHARE MODE")
            self.assertEqual(
                operations.for_share_sql(nowait=True),
                "LOCK IN SHARE MODE NOWAIT",
            )
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (10, 5, 0)
            _connection.mysql_is_mariadb = True
            operations = DatabaseOperations(_connection)
            self.assertEqual(operations.for_share_sql(), "LOCK IN SHARE MODE")
            self.assertEqual(
                operations.for_share_sql(nowait=True),
                "LOCK IN SHARE MODE NOWAIT",
            )
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (10, 6, 0)
            _connection.mysql_is_mariadb = True
            operations = DatabaseOperations(_connection)
            self.assertEqual(operations.for_share_sql(), "LOCK IN SHARE MODE")
            self.assertEqual(
                operations.for_share_sql(skip_locked=True),
                "LOCK IN SHARE MODE SKIP LOCKED",
            )
