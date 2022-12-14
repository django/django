import copy
import unittest
from io import StringIO
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db import (
    DEFAULT_DB_ALIAS,
    DatabaseError,
    NotSupportedError,
    connection,
    connections,
)
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import TestCase, override_settings


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class Tests(TestCase):
    databases = {"default", "other"}

    def test_nodb_cursor(self):
        """
        The _nodb_cursor() fallbacks to the default connection database when
        access to the 'postgres' database is not granted.
        """
        orig_connect = BaseDatabaseWrapper.connect

        def mocked_connect(self):
            if self.settings_dict["NAME"] is None:
                raise DatabaseError()
            return orig_connect(self)

        with connection._nodb_cursor() as cursor:
            self.assertIs(cursor.closed, False)
            self.assertIsNotNone(cursor.db.connection)
            self.assertIsNone(cursor.db.settings_dict["NAME"])
        self.assertIs(cursor.closed, True)
        self.assertIsNone(cursor.db.connection)

        # Now assume the 'postgres' db isn't available
        msg = (
            "Normally Django will use a connection to the 'postgres' database "
            "to avoid running initialization queries against the production "
            "database when it's not needed (for example, when running tests). "
            "Django was unable to create a connection to the 'postgres' "
            "database and will use the first PostgreSQL database instead."
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            with mock.patch(
                "django.db.backends.base.base.BaseDatabaseWrapper.connect",
                side_effect=mocked_connect,
                autospec=True,
            ):
                with mock.patch.object(
                    connection,
                    "settings_dict",
                    {**connection.settings_dict, "NAME": "postgres"},
                ):
                    with connection._nodb_cursor() as cursor:
                        self.assertIs(cursor.closed, False)
                        self.assertIsNotNone(cursor.db.connection)
        self.assertIs(cursor.closed, True)
        self.assertIsNone(cursor.db.connection)
        self.assertIsNotNone(cursor.db.settings_dict["NAME"])
        self.assertEqual(
            cursor.db.settings_dict["NAME"], connections["other"].settings_dict["NAME"]
        )
        # Cursor is yielded only for the first PostgreSQL database.
        with self.assertWarnsMessage(RuntimeWarning, msg):
            with mock.patch(
                "django.db.backends.base.base.BaseDatabaseWrapper.connect",
                side_effect=mocked_connect,
                autospec=True,
            ):
                with connection._nodb_cursor() as cursor:
                    self.assertIs(cursor.closed, False)
                    self.assertIsNotNone(cursor.db.connection)

    def test_nodb_cursor_raises_postgres_authentication_failure(self):
        """
        _nodb_cursor() re-raises authentication failure to the 'postgres' db
        when other connection to the PostgreSQL database isn't available.
        """

        def mocked_connect(self):
            raise DatabaseError()

        def mocked_all(self):
            test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
            test_connection.settings_dict = copy.deepcopy(connection.settings_dict)
            test_connection.settings_dict["NAME"] = "postgres"
            return [test_connection]

        msg = (
            "Normally Django will use a connection to the 'postgres' database "
            "to avoid running initialization queries against the production "
            "database when it's not needed (for example, when running tests). "
            "Django was unable to create a connection to the 'postgres' "
            "database and will use the first PostgreSQL database instead."
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            mocker_connections_all = mock.patch(
                "django.utils.connection.BaseConnectionHandler.all",
                side_effect=mocked_all,
                autospec=True,
            )
            mocker_connect = mock.patch(
                "django.db.backends.base.base.BaseDatabaseWrapper.connect",
                side_effect=mocked_connect,
                autospec=True,
            )
            with mocker_connections_all, mocker_connect:
                with self.assertRaises(DatabaseError):
                    with connection._nodb_cursor():
                        pass

    def test_nodb_cursor_reraise_exceptions(self):
        with self.assertRaisesMessage(DatabaseError, "exception"):
            with connection._nodb_cursor():
                raise DatabaseError("exception")

    def test_database_name_too_long(self):
        from django.db.backends.postgresql.base import DatabaseWrapper

        settings = connection.settings_dict.copy()
        max_name_length = connection.ops.max_name_length()
        settings["NAME"] = "a" + (max_name_length * "a")
        msg = (
            "The database name '%s' (%d characters) is longer than "
            "PostgreSQL's limit of %s characters. Supply a shorter NAME in "
            "settings.DATABASES."
        ) % (settings["NAME"], max_name_length + 1, max_name_length)
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DatabaseWrapper(settings).get_connection_params()

    def test_database_name_empty(self):
        from django.db.backends.postgresql.base import DatabaseWrapper

        settings = connection.settings_dict.copy()
        settings["NAME"] = ""
        msg = (
            "settings.DATABASES is improperly configured. Please supply the "
            "NAME or OPTIONS['service'] value."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DatabaseWrapper(settings).get_connection_params()

    def test_service_name(self):
        from django.db.backends.postgresql.base import DatabaseWrapper

        settings = connection.settings_dict.copy()
        settings["OPTIONS"] = {"service": "my_service"}
        settings["NAME"] = ""
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["service"], "my_service")
        self.assertNotIn("database", params)

    def test_service_name_default_db(self):
        # None is used to connect to the default 'postgres' db.
        from django.db.backends.postgresql.base import DatabaseWrapper

        settings = connection.settings_dict.copy()
        settings["NAME"] = None
        settings["OPTIONS"] = {"service": "django_test"}
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["dbname"], "postgres")
        self.assertNotIn("service", params)

    def test_connect_and_rollback(self):
        """
        PostgreSQL shouldn't roll back SET TIME ZONE, even if the first
        transaction is rolled back (#17062).
        """
        new_connection = connection.copy()
        try:
            # Ensure the database default time zone is different than
            # the time zone in new_connection.settings_dict. We can
            # get the default time zone by reset & show.
            with new_connection.cursor() as cursor:
                cursor.execute("RESET TIMEZONE")
                cursor.execute("SHOW TIMEZONE")
                db_default_tz = cursor.fetchone()[0]
            new_tz = "Europe/Paris" if db_default_tz == "UTC" else "UTC"
            new_connection.close()

            # Invalidate timezone name cache, because the setting_changed
            # handler cannot know about new_connection.
            del new_connection.timezone_name

            # Fetch a new connection with the new_tz as default
            # time zone, run a query and rollback.
            with self.settings(TIME_ZONE=new_tz):
                new_connection.set_autocommit(False)
                new_connection.rollback()

                # Now let's see if the rollback rolled back the SET TIME ZONE.
                with new_connection.cursor() as cursor:
                    cursor.execute("SHOW TIMEZONE")
                    tz = cursor.fetchone()[0]
                self.assertEqual(new_tz, tz)

        finally:
            new_connection.close()

    def test_connect_non_autocommit(self):
        """
        The connection wrapper shouldn't believe that autocommit is enabled
        after setting the time zone when AUTOCOMMIT is False (#21452).
        """
        new_connection = connection.copy()
        new_connection.settings_dict["AUTOCOMMIT"] = False

        try:
            # Open a database connection.
            with new_connection.cursor():
                self.assertFalse(new_connection.get_autocommit())
        finally:
            new_connection.close()

    def test_connect_isolation_level(self):
        """
        The transaction level can be configured with
        DATABASES ['OPTIONS']['isolation_level'].
        """
        from django.db.backends.postgresql.psycopg_any import IsolationLevel

        # Since this is a django.test.TestCase, a transaction is in progress
        # and the isolation level isn't reported as 0. This test assumes that
        # PostgreSQL is configured with the default isolation level.
        # Check the level on the psycopg2 connection, not the Django wrapper.
        self.assertIsNone(connection.connection.isolation_level)

        new_connection = connection.copy()
        new_connection.settings_dict["OPTIONS"][
            "isolation_level"
        ] = IsolationLevel.SERIALIZABLE
        try:
            # Start a transaction so the isolation level isn't reported as 0.
            new_connection.set_autocommit(False)
            # Check the level on the psycopg2 connection, not the Django wrapper.
            self.assertEqual(
                new_connection.connection.isolation_level,
                IsolationLevel.SERIALIZABLE,
            )
        finally:
            new_connection.close()

    def test_connect_invalid_isolation_level(self):
        self.assertIsNone(connection.connection.isolation_level)
        new_connection = connection.copy()
        new_connection.settings_dict["OPTIONS"]["isolation_level"] = -1
        msg = (
            "Invalid transaction isolation level -1 specified. Use one of the "
            "IsolationLevel values."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            new_connection.ensure_connection()

    def test_connect_no_is_usable_checks(self):
        new_connection = connection.copy()
        try:
            with mock.patch.object(new_connection, "is_usable") as is_usable:
                new_connection.connect()
            is_usable.assert_not_called()
        finally:
            new_connection.close()

    def _select(self, val):
        with connection.cursor() as cursor:
            cursor.execute("SELECT %s", (val,))
            return cursor.fetchone()[0]

    def test_select_ascii_array(self):
        a = ["awef"]
        b = self._select(a)
        self.assertEqual(a[0], b[0])

    def test_select_unicode_array(self):
        a = ["ᄲawef"]
        b = self._select(a)
        self.assertEqual(a[0], b[0])

    def test_lookup_cast(self):
        from django.db.backends.postgresql.operations import DatabaseOperations

        do = DatabaseOperations(connection=None)
        lookups = (
            "iexact",
            "contains",
            "icontains",
            "startswith",
            "istartswith",
            "endswith",
            "iendswith",
            "regex",
            "iregex",
        )
        for lookup in lookups:
            with self.subTest(lookup=lookup):
                self.assertIn("::text", do.lookup_cast(lookup))
        # RemovedInDjango51Warning.
        for lookup in lookups:
            for field_type in ("CICharField", "CIEmailField", "CITextField"):
                with self.subTest(lookup=lookup, field_type=field_type):
                    self.assertIn(
                        "::citext", do.lookup_cast(lookup, internal_type=field_type)
                    )

    def test_correct_extraction_psycopg_version(self):
        from django.db.backends.postgresql.base import Database, psycopg2_version

        with mock.patch.object(Database, "__version__", "4.2.1 (dt dec pq3 ext lo64)"):
            self.assertEqual(psycopg2_version(), (4, 2, 1))
        with mock.patch.object(
            Database, "__version__", "4.2b0.dev1 (dt dec pq3 ext lo64)"
        ):
            self.assertEqual(psycopg2_version(), (4, 2))

    @override_settings(DEBUG=True)
    def test_copy_cursors(self):
        out = StringIO()
        copy_expert_sql = "COPY django_session TO STDOUT (FORMAT CSV, HEADER)"
        with connection.cursor() as cursor:
            cursor.copy_expert(copy_expert_sql, out)
            cursor.copy_to(out, "django_session")
        self.assertEqual(
            [q["sql"] for q in connection.queries],
            [copy_expert_sql, "COPY django_session TO STDOUT"],
        )

    def test_get_database_version(self):
        new_connection = connection.copy()
        new_connection.pg_version = 110009
        self.assertEqual(new_connection.get_database_version(), (11, 9))

    @mock.patch.object(connection, "get_database_version", return_value=(11,))
    def test_check_database_version_supported(self, mocked_get_database_version):
        msg = "PostgreSQL 12 or later is required (found 11)."
        with self.assertRaisesMessage(NotSupportedError, msg):
            connection.check_database_version_supported()
        self.assertTrue(mocked_get_database_version.called)
