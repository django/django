import unittest
from io import StringIO
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection, connections
from django.test import TestCase, override_settings


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests')
class Tests(TestCase):

    def test_nodb_connection(self):
        """
        The _nodb_connection property fallbacks to the default connection
        database when access to the 'postgres' database is not granted.
        """
        def mocked_connect(self):
            if self.settings_dict['NAME'] is None:
                raise DatabaseError()
            return ''

        nodb_conn = connection._nodb_connection
        self.assertIsNone(nodb_conn.settings_dict['NAME'])

        # Now assume the 'postgres' db isn't available
        msg = (
            "Normally Django will use a connection to the 'postgres' database "
            "to avoid running initialization queries against the production "
            "database when it's not needed (for example, when running tests). "
            "Django was unable to create a connection to the 'postgres' "
            "database and will use the first PostgreSQL database instead."
        )
        with self.assertWarnsMessage(RuntimeWarning, msg):
            with mock.patch('django.db.backends.base.base.BaseDatabaseWrapper.connect',
                            side_effect=mocked_connect, autospec=True):
                with mock.patch.object(
                    connection,
                    'settings_dict',
                    {**connection.settings_dict, 'NAME': 'postgres'},
                ):
                    nodb_conn = connection._nodb_connection
        self.assertIsNotNone(nodb_conn.settings_dict['NAME'])
        self.assertEqual(nodb_conn.settings_dict['NAME'], connections['other'].settings_dict['NAME'])

    def test_database_name_too_long(self):
        from django.db.backends.postgresql.base import DatabaseWrapper
        settings = connection.settings_dict.copy()
        max_name_length = connection.ops.max_name_length()
        settings['NAME'] = 'a' + (max_name_length * 'a')
        msg = (
            "The database name '%s' (%d characters) is longer than "
            "PostgreSQL's limit of %s characters. Supply a shorter NAME in "
            "settings.DATABASES."
        ) % (settings['NAME'], max_name_length + 1, max_name_length)
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DatabaseWrapper(settings).get_connection_params()

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
            new_tz = 'Europe/Paris' if db_default_tz == 'UTC' else 'UTC'
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
        new_connection.settings_dict['AUTOCOMMIT'] = False

        try:
            # Open a database connection.
            new_connection.cursor()
            self.assertFalse(new_connection.get_autocommit())
        finally:
            new_connection.close()

    def test_connect_isolation_level(self):
        """
        The transaction level can be configured with
        DATABASES ['OPTIONS']['isolation_level'].
        """
        import psycopg2
        from psycopg2.extensions import (
            ISOLATION_LEVEL_READ_COMMITTED as read_committed,
            ISOLATION_LEVEL_SERIALIZABLE as serializable,
        )
        # Since this is a django.test.TestCase, a transaction is in progress
        # and the isolation level isn't reported as 0. This test assumes that
        # PostgreSQL is configured with the default isolation level.

        # Check the level on the psycopg2 connection, not the Django wrapper.
        default_level = read_committed if psycopg2.__version__ < '2.7' else None
        self.assertEqual(connection.connection.isolation_level, default_level)

        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = serializable
        try:
            # Start a transaction so the isolation level isn't reported as 0.
            new_connection.set_autocommit(False)
            # Check the level on the psycopg2 connection, not the Django wrapper.
            self.assertEqual(new_connection.connection.isolation_level, serializable)
        finally:
            new_connection.close()

    def test_connect_no_is_usable_checks(self):
        new_connection = connection.copy()
        with mock.patch.object(new_connection, 'is_usable') as is_usable:
            new_connection.connect()
        is_usable.assert_not_called()

    def _select(self, val):
        with connection.cursor() as cursor:
            cursor.execute('SELECT %s', (val,))
            return cursor.fetchone()[0]

    def test_select_ascii_array(self):
        a = ['awef']
        b = self._select(a)
        self.assertEqual(a[0], b[0])

    def test_select_unicode_array(self):
        a = ['ᄲawef']
        b = self._select(a)
        self.assertEqual(a[0], b[0])

    def test_lookup_cast(self):
        from django.db.backends.postgresql.operations import DatabaseOperations
        do = DatabaseOperations(connection=None)
        lookups = (
            'iexact', 'contains', 'icontains', 'startswith', 'istartswith',
            'endswith', 'iendswith', 'regex', 'iregex',
        )
        for lookup in lookups:
            with self.subTest(lookup=lookup):
                self.assertIn('::text', do.lookup_cast(lookup))
        for lookup in lookups:
            for field_type in ('CICharField', 'CIEmailField', 'CITextField'):
                with self.subTest(lookup=lookup, field_type=field_type):
                    self.assertIn('::citext', do.lookup_cast(lookup, internal_type=field_type))

    def test_correct_extraction_psycopg2_version(self):
        from django.db.backends.postgresql.base import psycopg2_version
        with mock.patch('psycopg2.__version__', '4.2.1 (dt dec pq3 ext lo64)'):
            self.assertEqual(psycopg2_version(), (4, 2, 1))
        with mock.patch('psycopg2.__version__', '4.2b0.dev1 (dt dec pq3 ext lo64)'):
            self.assertEqual(psycopg2_version(), (4, 2))

    @override_settings(DEBUG=True)
    def test_copy_cursors(self):
        out = StringIO()
        copy_expert_sql = 'COPY django_session TO STDOUT (FORMAT CSV, HEADER)'
        with connection.cursor() as cursor:
            cursor.copy_expert(copy_expert_sql, out)
            cursor.copy_to(out, 'django_session')
        self.assertEqual(
            [q['sql'] for q in connection.queries],
            [copy_expert_sql, 'COPY django_session TO STDOUT'],
        )
