# -*- coding: utf-8 -*-
# Unit and doctests for specific database backends.
from __future__ import unicode_literals

import datetime
import re
import threading
import unittest
import warnings
from decimal import Decimal, Rounded

from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import no_style
from django.db import (
    DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, connection, connections,
    reset_queries, transaction,
)
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.postgresql import version as pg_version
from django.db.backends.signals import connection_created
from django.db.backends.utils import CursorWrapper, format_number
from django.db.models import Avg, StdDev, Sum, Variance
from django.db.models.sql.constants import CURSOR
from django.db.utils import ConnectionHandler
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, mock, override_settings,
    skipIfDBFeature, skipUnlessDBFeature,
)
from django.utils import six
from django.utils.six.moves import range

from .models import (
    Article, Item, Object, ObjectReference, Person, Post, RawData, Reporter,
    ReporterProxy, SchoolClass, Square,
    VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ,
)


class DatabaseWrapperTests(SimpleTestCase):

    def test_initialization_class_attributes(self):
        """
        The "initialization" class attributes like client_class and
        creation_class should be set on the class and reflected in the
        corresponding instance attributes of the instantiated backend.
        """
        conn = connections[DEFAULT_DB_ALIAS]
        conn_class = type(conn)
        attr_names = [
            ('client_class', 'client'),
            ('creation_class', 'creation'),
            ('features_class', 'features'),
            ('introspection_class', 'introspection'),
            ('ops_class', 'ops'),
            ('validation_class', 'validation'),
        ]
        for class_attr_name, instance_attr_name in attr_names:
            class_attr_value = getattr(conn_class, class_attr_name)
            self.assertIsNotNone(class_attr_value)
            instance_attr_value = getattr(conn, instance_attr_name)
            self.assertIsInstance(instance_attr_value, class_attr_value)


class DummyBackendTest(SimpleTestCase):

    def test_no_databases(self):
        """
        Empty DATABASES setting default to the dummy backend.
        """
        DATABASES = {}
        conns = ConnectionHandler(DATABASES)
        self.assertEqual(conns[DEFAULT_DB_ALIAS].settings_dict['ENGINE'], 'django.db.backends.dummy')
        with self.assertRaises(ImproperlyConfigured):
            conns[DEFAULT_DB_ALIAS].ensure_connection()


@unittest.skipUnless(connection.vendor == 'oracle', "Test only for Oracle")
class OracleTests(unittest.TestCase):

    def test_quote_name(self):
        # '%' chars are escaped for query execution.
        name = '"SOME%NAME"'
        quoted_name = connection.ops.quote_name(name)
        self.assertEqual(quoted_name % (), name)

    def test_dbms_session(self):
        # If the backend is Oracle, test that we can call a standard
        # stored procedure through our cursor wrapper.
        with connection.cursor() as cursor:
            cursor.callproc('DBMS_SESSION.SET_IDENTIFIER', ['_django_testing!'])

    def test_cursor_var(self):
        # If the backend is Oracle, test that we can pass cursor variables
        # as query parameters.
        from django.db.backends.oracle.base import Database

        with connection.cursor() as cursor:
            var = cursor.var(Database.STRING)
            cursor.execute("BEGIN %s := 'X'; END; ", [var])
            self.assertEqual(var.getvalue(), 'X')

    def test_long_string(self):
        # If the backend is Oracle, test that we can save a text longer
        # than 4000 chars and read it properly
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE ltext ("TEXT" NCLOB)')
            long_str = ''.join(six.text_type(x) for x in range(4000))
            cursor.execute('INSERT INTO ltext VALUES (%s)', [long_str])
            cursor.execute('SELECT text FROM ltext')
            row = cursor.fetchone()
            self.assertEqual(long_str, row[0].read())
            cursor.execute('DROP TABLE ltext')

    def test_client_encoding(self):
        # If the backend is Oracle, test that the client encoding is set
        # correctly.  This was broken under Cygwin prior to r14781.
        connection.ensure_connection()
        self.assertEqual(connection.connection.encoding, "UTF-8")
        self.assertEqual(connection.connection.nencoding, "UTF-8")

    def test_order_of_nls_parameters(self):
        # an 'almost right' datetime should work with configured
        # NLS parameters as per #18465.
        with connection.cursor() as cursor:
            query = "select 1 from dual where '1936-12-29 00:00' < sysdate"
            # The query succeeds without errors - pre #18465 this
            # wasn't the case.
            cursor.execute(query)
            self.assertEqual(cursor.fetchone()[0], 1)


@unittest.skipUnless(connection.vendor == 'sqlite', "Test only for SQLite")
class SQLiteTests(TestCase):

    longMessage = True

    def test_autoincrement(self):
        """
        auto_increment fields are created with the AUTOINCREMENT keyword
        in order to be monotonically increasing. Refs #10164.
        """
        with connection.schema_editor(collect_sql=True) as editor:
            editor.create_model(Square)
            statements = editor.collected_sql
        match = re.search('"id" ([^,]+),', statements[0])
        self.assertIsNotNone(match)
        self.assertEqual(
            'integer NOT NULL PRIMARY KEY AUTOINCREMENT',
            match.group(1),
            "Wrong SQL used to create an auto-increment column on SQLite"
        )

    def test_aggregation(self):
        """
        #19360: Raise NotImplementedError when aggregating on date/time fields.
        """
        for aggregate in (Sum, Avg, Variance, StdDev):
            with self.assertRaises(NotImplementedError):
                Item.objects.all().aggregate(aggregate('time'))
            with self.assertRaises(NotImplementedError):
                Item.objects.all().aggregate(aggregate('date'))
            with self.assertRaises(NotImplementedError):
                Item.objects.all().aggregate(aggregate('last_modified'))
            with self.assertRaises(NotImplementedError):
                Item.objects.all().aggregate(
                    **{'complex': aggregate('last_modified') + aggregate('last_modified')}
                )

    def test_memory_db_test_name(self):
        """
        A named in-memory db should be allowed where supported.
        """
        from django.db.backends.sqlite3.base import DatabaseWrapper
        settings_dict = {
            'TEST': {
                'NAME': 'file:memorydb_test?mode=memory&cache=shared',
            }
        }
        wrapper = DatabaseWrapper(settings_dict)
        creation = wrapper.creation
        if creation.connection.features.can_share_in_memory_db:
            expected = creation.connection.settings_dict['TEST']['NAME']
            self.assertEqual(creation._get_test_db_name(), expected)
        else:
            msg = (
                "Using a shared memory database with `mode=memory` in the "
                "database name is not supported in your environment, "
                "use `:memory:` instead."
            )
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                creation._get_test_db_name()


@unittest.skipUnless(connection.vendor == 'postgresql', "Test only for PostgreSQL")
class PostgreSQLTests(TestCase):

    def assert_parses(self, version_string, version):
        self.assertEqual(pg_version._parse_version(version_string), version)

    def test_parsing(self):
        """Test PostgreSQL version parsing from `SELECT version()` output"""
        self.assert_parses("PostgreSQL 9.3 beta4", 90300)
        self.assert_parses("PostgreSQL 9.3", 90300)
        self.assert_parses("EnterpriseDB 9.3", 90300)
        self.assert_parses("PostgreSQL 9.3.6", 90306)
        self.assert_parses("PostgreSQL 9.4beta1", 90400)
        self.assert_parses(
            "PostgreSQL 9.3.1 on i386-apple-darwin9.2.2, compiled by GCC "
            "i686-apple-darwin9-gcc-4.0.1 (GCC) 4.0.1 (Apple Inc. build 5478)",
            90301
        )

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
        with warnings.catch_warnings(record=True) as w:
            with mock.patch('django.db.backends.base.base.BaseDatabaseWrapper.connect',
                            side_effect=mocked_connect, autospec=True):
                warnings.simplefilter('always', RuntimeWarning)
                nodb_conn = connection._nodb_connection
        self.assertIsNotNone(nodb_conn.settings_dict['NAME'])
        self.assertEqual(nodb_conn.settings_dict['NAME'], connection.settings_dict['NAME'])
        # Check a RuntimeWarning has been emitted
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0].message.__class__, RuntimeWarning)

    def test_version_detection(self):
        """Test PostgreSQL version detection"""

        # Helper mocks
        class CursorMock(object):
            "Very simple mock of DB-API cursor"
            def execute(self, arg):
                pass

            def fetchone(self):
                return ["PostgreSQL 9.3"]

            def __enter__(self):
                return self

            def __exit__(self, type, value, traceback):
                pass

        class OlderConnectionMock(object):
            "Mock of psycopg2 (< 2.0.12) connection"
            def cursor(self):
                return CursorMock()

        # psycopg2 < 2.0.12 code path
        conn = OlderConnectionMock()
        self.assertEqual(pg_version.get_version(conn), 90300)

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
            cursor = new_connection.cursor()
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
                cursor = new_connection.cursor()
                new_connection.rollback()

                # Now let's see if the rollback rolled back the SET TIME ZONE.
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
        Regression test for #18130 and #24318.
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
        for lookup in ('iexact', 'contains', 'icontains', 'startswith',
                       'istartswith', 'endswith', 'iendswith', 'regex', 'iregex'):
            self.assertIn('::text', do.lookup_cast(lookup))

    def test_correct_extraction_psycopg2_version(self):
        from django.db.backends.postgresql.base import psycopg2_version
        version_path = 'django.db.backends.postgresql.base.Database.__version__'

        with mock.patch(version_path, '2.6.9'):
            self.assertEqual(psycopg2_version(), (2, 6, 9))

        with mock.patch(version_path, '2.5.dev0'):
            self.assertEqual(psycopg2_version(), (2, 5))


class DateQuotingTest(TestCase):

    def test_django_date_trunc(self):
        """
        Test the custom ``django_date_trunc method``, in particular against
        fields which clash with strings passed to it (e.g. 'year') (#12818).
        """
        updated = datetime.datetime(2010, 2, 20)
        SchoolClass.objects.create(year=2009, last_updated=updated)
        years = SchoolClass.objects.dates('last_updated', 'year')
        self.assertEqual(list(years), [datetime.date(2010, 1, 1)])

    def test_django_date_extract(self):
        """
        Test the custom ``django_date_extract method``, in particular against fields
        which clash with strings passed to it (e.g. 'day') (#12818).
        """
        updated = datetime.datetime(2010, 2, 20)
        SchoolClass.objects.create(year=2009, last_updated=updated)
        classes = SchoolClass.objects.filter(last_updated__day=20)
        self.assertEqual(len(classes), 1)


@override_settings(DEBUG=True)
class LastExecutedQueryTest(TestCase):

    def test_last_executed_query(self):
        """
        last_executed_query should not raise an exception even if no previous
        query has been run.
        """
        cursor = connection.cursor()
        connection.ops.last_executed_query(cursor, '', ())

    def test_debug_sql(self):
        list(Reporter.objects.filter(first_name="test"))
        sql = connection.queries[-1]['sql'].lower()
        self.assertIn("select", sql)
        self.assertIn(Reporter._meta.db_table, sql)

    def test_query_encoding(self):
        """
        last_executed_query() returns an Unicode string
        """
        data = RawData.objects.filter(raw_data=b'\x00\x46  \xFE').extra(select={'föö': 1})
        sql, params = data.query.sql_with_params()
        cursor = data.query.get_compiler('default').execute_sql(CURSOR)
        last_sql = cursor.db.ops.last_executed_query(cursor, sql, params)
        self.assertIsInstance(last_sql, six.text_type)

    @unittest.skipUnless(connection.vendor == 'sqlite',
                         "This test is specific to SQLite.")
    def test_no_interpolation_on_sqlite(self):
        # This shouldn't raise an exception (##17158)
        query = "SELECT strftime('%Y', 'now');"
        connection.cursor().execute(query)
        self.assertEqual(connection.queries[-1]['sql'], query)

    @unittest.skipUnless(connection.vendor == 'sqlite',
                         "This test is specific to SQLite.")
    def test_parameter_quoting_on_sqlite(self):
        # The implementation of last_executed_queries isn't optimal. It's
        # worth testing that parameters are quoted. See #14091.
        query = "SELECT %s"
        params = ["\"'\\"]
        connection.cursor().execute(query, params)
        # Note that the single quote is repeated
        substituted = "SELECT '\"''\\'"
        self.assertEqual(connection.queries[-1]['sql'], substituted)

    @unittest.skipUnless(connection.vendor == 'sqlite',
                         "This test is specific to SQLite.")
    def test_large_number_of_parameters_on_sqlite(self):
        # If SQLITE_MAX_VARIABLE_NUMBER (default = 999) has been changed to be
        # greater than SQLITE_MAX_COLUMN (default = 2000), last_executed_query
        # can hit the SQLITE_MAX_COLUMN limit. See #26063.
        cursor = connection.cursor()
        sql = "SELECT MAX(%s)" % ", ".join(["%s"] * 2001)
        params = list(range(2001))
        # This should not raise an exception.
        cursor.db.ops.last_executed_query(cursor.cursor, sql, params)


class ParameterHandlingTest(TestCase):

    def test_bad_parameter_count(self):
        "An executemany call with too many/not enough parameters will raise an exception (Refs #12612)"
        cursor = connection.cursor()
        query = ('INSERT INTO %s (%s, %s) VALUES (%%s, %%s)' % (
            connection.introspection.table_name_converter('backends_square'),
            connection.ops.quote_name('root'),
            connection.ops.quote_name('square')
        ))
        with self.assertRaises(Exception):
            cursor.executemany(query, [(1, 2, 3)])
        with self.assertRaises(Exception):
            cursor.executemany(query, [(1,)])


class LongNameTest(TransactionTestCase):
    """Long primary keys and model names can result in a sequence name
    that exceeds the database limits, which will result in truncation
    on certain databases (e.g., Postgres). The backend needs to use
    the correct sequence name in last_insert_id and other places, so
    check it is. Refs #8901.
    """
    available_apps = ['backends']

    def test_sequence_name_length_limits_create(self):
        """Test creation of model with long name and long pk name doesn't error. Ref #8901"""
        VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ.objects.create()

    def test_sequence_name_length_limits_m2m(self):
        """
        An m2m save of a model with a long name and a long m2m field name
        doesn't error (#8901).
        """
        obj = VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ.objects.create()
        rel_obj = Person.objects.create(first_name='Django', last_name='Reinhardt')
        obj.m2m_also_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz.add(rel_obj)

    def test_sequence_name_length_limits_flush(self):
        """
        Sequence resetting as part of a flush with model with long name and
        long pk name doesn't error (#8901).
        """
        # A full flush is expensive to the full test, so we dig into the
        # internals to generate the likely offending SQL and run it manually

        # Some convenience aliases
        VLM = VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
        VLM_m2m = VLM.m2m_also_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz.through
        tables = [
            VLM._meta.db_table,
            VLM_m2m._meta.db_table,
        ]
        sequences = [
            {
                'column': VLM._meta.pk.column,
                'table': VLM._meta.db_table
            },
        ]
        cursor = connection.cursor()
        for statement in connection.ops.sql_flush(no_style(), tables, sequences):
            cursor.execute(statement)


class SequenceResetTest(TestCase):

    def test_generic_relation(self):
        "Sequence names are correct when resetting generic relations (Ref #13941)"
        # Create an object with a manually specified PK
        Post.objects.create(id=10, name='1st post', text='hello world')

        # Reset the sequences for the database
        cursor = connection.cursor()
        commands = connections[DEFAULT_DB_ALIAS].ops.sequence_reset_sql(no_style(), [Post])
        for sql in commands:
            cursor.execute(sql)

        # If we create a new object now, it should have a PK greater
        # than the PK we specified manually.
        obj = Post.objects.create(name='New post', text='goodbye world')
        self.assertGreater(obj.pk, 10)


# This test needs to run outside of a transaction, otherwise closing the
# connection would implicitly rollback and cause problems during teardown.
class ConnectionCreatedSignalTest(TransactionTestCase):

    available_apps = []

    # Unfortunately with sqlite3 the in-memory test database cannot be closed,
    # and so it cannot be re-opened during testing.
    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_signal(self):
        data = {}

        def receiver(sender, connection, **kwargs):
            data["connection"] = connection

        connection_created.connect(receiver)
        connection.close()
        connection.cursor()
        self.assertIs(data["connection"].connection, connection.connection)

        connection_created.disconnect(receiver)
        data.clear()
        connection.cursor()
        self.assertEqual(data, {})


class EscapingChecks(TestCase):
    """
    All tests in this test case are also run with settings.DEBUG=True in
    EscapingChecksDebug test case, to also test CursorDebugWrapper.
    """

    bare_select_suffix = connection.features.bare_select_suffix

    def test_paramless_no_escaping(self):
        cursor = connection.cursor()
        cursor.execute("SELECT '%s'" + self.bare_select_suffix)
        self.assertEqual(cursor.fetchall()[0][0], '%s')

    def test_parameter_escaping(self):
        cursor = connection.cursor()
        cursor.execute("SELECT '%%', %s" + self.bare_select_suffix, ('%d',))
        self.assertEqual(cursor.fetchall()[0], ('%', '%d'))

    @unittest.skipUnless(connection.vendor == 'sqlite',
                         "This is an sqlite-specific issue")
    def test_sqlite_parameter_escaping(self):
        # '%s' escaping support for sqlite3 #13648
        cursor = connection.cursor()
        cursor.execute("select strftime('%s', date('now'))")
        response = cursor.fetchall()[0][0]
        # response should be an non-zero integer
        self.assertTrue(int(response))


@override_settings(DEBUG=True)
class EscapingChecksDebug(EscapingChecks):
    pass


class BackendTestCase(TransactionTestCase):

    available_apps = ['backends']

    def create_squares_with_executemany(self, args):
        self.create_squares(args, 'format', True)

    def create_squares(self, args, paramstyle, multiple):
        cursor = connection.cursor()
        opts = Square._meta
        tbl = connection.introspection.table_name_converter(opts.db_table)
        f1 = connection.ops.quote_name(opts.get_field('root').column)
        f2 = connection.ops.quote_name(opts.get_field('square').column)
        if paramstyle == 'format':
            query = 'INSERT INTO %s (%s, %s) VALUES (%%s, %%s)' % (tbl, f1, f2)
        elif paramstyle == 'pyformat':
            query = 'INSERT INTO %s (%s, %s) VALUES (%%(root)s, %%(square)s)' % (tbl, f1, f2)
        else:
            raise ValueError("unsupported paramstyle in test")
        if multiple:
            cursor.executemany(query, args)
        else:
            cursor.execute(query, args)

    def test_cursor_executemany(self):
        # Test cursor.executemany #4896
        args = [(i, i ** 2) for i in range(-5, 6)]
        self.create_squares_with_executemany(args)
        self.assertEqual(Square.objects.count(), 11)
        for i in range(-5, 6):
            square = Square.objects.get(root=i)
            self.assertEqual(square.square, i ** 2)

    def test_cursor_executemany_with_empty_params_list(self):
        # Test executemany with params=[] does nothing #4765
        args = []
        self.create_squares_with_executemany(args)
        self.assertEqual(Square.objects.count(), 0)

    def test_cursor_executemany_with_iterator(self):
        # Test executemany accepts iterators #10320
        args = iter((i, i ** 2) for i in range(-3, 2))
        self.create_squares_with_executemany(args)
        self.assertEqual(Square.objects.count(), 5)

        args = iter((i, i ** 2) for i in range(3, 7))
        with override_settings(DEBUG=True):
            # same test for DebugCursorWrapper
            self.create_squares_with_executemany(args)
        self.assertEqual(Square.objects.count(), 9)

    @skipUnlessDBFeature('supports_paramstyle_pyformat')
    def test_cursor_execute_with_pyformat(self):
        # Support pyformat style passing of parameters #10070
        args = {'root': 3, 'square': 9}
        self.create_squares(args, 'pyformat', multiple=False)
        self.assertEqual(Square.objects.count(), 1)

    @skipUnlessDBFeature('supports_paramstyle_pyformat')
    def test_cursor_executemany_with_pyformat(self):
        # Support pyformat style passing of parameters #10070
        args = [{'root': i, 'square': i ** 2} for i in range(-5, 6)]
        self.create_squares(args, 'pyformat', multiple=True)
        self.assertEqual(Square.objects.count(), 11)
        for i in range(-5, 6):
            square = Square.objects.get(root=i)
            self.assertEqual(square.square, i ** 2)

    @skipUnlessDBFeature('supports_paramstyle_pyformat')
    def test_cursor_executemany_with_pyformat_iterator(self):
        args = iter({'root': i, 'square': i ** 2} for i in range(-3, 2))
        self.create_squares(args, 'pyformat', multiple=True)
        self.assertEqual(Square.objects.count(), 5)

        args = iter({'root': i, 'square': i ** 2} for i in range(3, 7))
        with override_settings(DEBUG=True):
            # same test for DebugCursorWrapper
            self.create_squares(args, 'pyformat', multiple=True)
        self.assertEqual(Square.objects.count(), 9)

    def test_cursor_close_failure_does_not_mask_original_exception(self):
        persons = Person.objects.iterator()

        def raise_original_exception(*args, **kwargs):
            raise Exception('Real exception raised by the database on cursor.execute')

        def raise_close_exception():
            raise Exception(
                'Error when attempting to close the cursor, this exception should not mask the original exception'
            )

        mock_cursor = connection.chunked_cursor()
        mock_cursor.execute = mock.MagicMock(side_effect=raise_original_exception)
        mock_cursor.close = mock.MagicMock(side_effect=raise_close_exception)

        with self.assertRaisesMessage(Exception, 'Real exception raised by the database on cursor.execute'):
            with mock.patch('django.db.connection.create_cursor', return_value=mock_cursor):
                list(persons)

    def test_unicode_fetches(self):
        # fetchone, fetchmany, fetchall return strings as unicode objects #6254
        qn = connection.ops.quote_name
        Person(first_name="John", last_name="Doe").save()
        Person(first_name="Jane", last_name="Doe").save()
        Person(first_name="Mary", last_name="Agnelline").save()
        Person(first_name="Peter", last_name="Parker").save()
        Person(first_name="Clark", last_name="Kent").save()
        opts2 = Person._meta
        f3, f4 = opts2.get_field('first_name'), opts2.get_field('last_name')
        cursor = connection.cursor()
        cursor.execute(
            'SELECT %s, %s FROM %s ORDER BY %s' % (
                qn(f3.column),
                qn(f4.column),
                connection.introspection.table_name_converter(opts2.db_table),
                qn(f3.column),
            )
        )
        self.assertEqual(cursor.fetchone(), ('Clark', 'Kent'))
        self.assertEqual(list(cursor.fetchmany(2)), [('Jane', 'Doe'), ('John', 'Doe')])
        self.assertEqual(list(cursor.fetchall()), [('Mary', 'Agnelline'), ('Peter', 'Parker')])

    def test_unicode_password(self):
        old_password = connection.settings_dict['PASSWORD']
        connection.settings_dict['PASSWORD'] = "françois"
        try:
            connection.cursor()
        except DatabaseError:
            # As password is probably wrong, a database exception is expected
            pass
        except Exception as e:
            self.fail("Unexpected error raised with unicode password: %s" % e)
        finally:
            connection.settings_dict['PASSWORD'] = old_password

    def test_database_operations_helper_class(self):
        # Ticket #13630
        self.assertTrue(hasattr(connection, 'ops'))
        self.assertTrue(hasattr(connection.ops, 'connection'))
        self.assertEqual(connection, connection.ops.connection)

    def test_database_operations_init(self):
        """
        DatabaseOperations initialization doesn't query the database.
        See #17656.
        """
        with self.assertNumQueries(0):
            connection.ops.__class__(connection)

    def test_cached_db_features(self):
        self.assertIn(connection.features.supports_transactions, (True, False))
        self.assertIn(connection.features.supports_stddev, (True, False))
        self.assertIn(connection.features.can_introspect_foreign_keys, (True, False))

    def test_duplicate_table_error(self):
        """ Creating an existing table returns a DatabaseError """
        cursor = connection.cursor()
        query = 'CREATE TABLE %s (id INTEGER);' % Article._meta.db_table
        with self.assertRaises(DatabaseError):
            cursor.execute(query)

    def test_cursor_contextmanager(self):
        """
        Cursors can be used as a context manager
        """
        with connection.cursor() as cursor:
            self.assertIsInstance(cursor, CursorWrapper)
        # Both InterfaceError and ProgrammingError seem to be used when
        # accessing closed cursor (psycopg2 has InterfaceError, rest seem
        # to use ProgrammingError).
        with self.assertRaises(connection.features.closed_cursor_error_class):
            # cursor should be closed, so no queries should be possible.
            cursor.execute("SELECT 1" + connection.features.bare_select_suffix)

    @unittest.skipUnless(connection.vendor == 'postgresql',
                         "Psycopg2 specific cursor.closed attribute needed")
    def test_cursor_contextmanager_closing(self):
        # There isn't a generic way to test that cursors are closed, but
        # psycopg2 offers us a way to check that by closed attribute.
        # So, run only on psycopg2 for that reason.
        with connection.cursor() as cursor:
            self.assertIsInstance(cursor, CursorWrapper)
        self.assertTrue(cursor.closed)

    # Unfortunately with sqlite3 the in-memory test database cannot be closed.
    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_is_usable_after_database_disconnects(self):
        """
        is_usable() doesn't crash when the database disconnects (#21553).
        """
        # Open a connection to the database.
        with connection.cursor():
            pass
        # Emulate a connection close by the database.
        connection._close()
        # Even then is_usable() should not raise an exception.
        try:
            self.assertFalse(connection.is_usable())
        finally:
            # Clean up the mess created by connection._close(). Since the
            # connection is already closed, this crashes on some backends.
            try:
                connection.close()
            except Exception:
                pass

    @override_settings(DEBUG=True)
    def test_queries(self):
        """
        Test the documented API of connection.queries.
        """
        with connection.cursor() as cursor:
            reset_queries()
            cursor.execute("SELECT 1" + connection.features.bare_select_suffix)
        self.assertEqual(1, len(connection.queries))

        self.assertIsInstance(connection.queries, list)
        self.assertIsInstance(connection.queries[0], dict)
        self.assertCountEqual(connection.queries[0].keys(), ['sql', 'time'])

        reset_queries()
        self.assertEqual(0, len(connection.queries))

    # Unfortunately with sqlite3 the in-memory test database cannot be closed.
    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    @override_settings(DEBUG=True)
    def test_queries_limit(self):
        """
        The backend doesn't store an unlimited number of queries (#12581).
        """
        old_queries_limit = BaseDatabaseWrapper.queries_limit
        BaseDatabaseWrapper.queries_limit = 3
        new_connection = connection.copy()

        # Initialize the connection and clear initialization statements.
        with new_connection.cursor():
            pass
        new_connection.queries_log.clear()

        try:
            with new_connection.cursor() as cursor:
                cursor.execute("SELECT 1" + new_connection.features.bare_select_suffix)
                cursor.execute("SELECT 2" + new_connection.features.bare_select_suffix)

            with warnings.catch_warnings(record=True) as w:
                self.assertEqual(2, len(new_connection.queries))
                self.assertEqual(0, len(w))

            with new_connection.cursor() as cursor:
                cursor.execute("SELECT 3" + new_connection.features.bare_select_suffix)
                cursor.execute("SELECT 4" + new_connection.features.bare_select_suffix)

            with warnings.catch_warnings(record=True) as w:
                self.assertEqual(3, len(new_connection.queries))
                self.assertEqual(1, len(w))
                self.assertEqual(
                    str(w[0].message),
                    "Limit for query logging exceeded, only the last 3 queries will be returned."
                )
        finally:
            BaseDatabaseWrapper.queries_limit = old_queries_limit
            new_connection.close()

    def test_timezone_none_use_tz_false(self):
        connection.ensure_connection()
        with self.settings(TIME_ZONE=None, USE_TZ=False):
            connection.init_connection_state()


# We don't make these tests conditional because that means we would need to
# check and differentiate between:
# * MySQL+InnoDB, MySQL+MYISAM (something we currently can't do).
# * if sqlite3 (if/once we get #14204 fixed) has referential integrity turned
#   on or not, something that would be controlled by runtime support and user
#   preference.
# verify if its type is django.database.db.IntegrityError.
class FkConstraintsTests(TransactionTestCase):

    available_apps = ['backends']

    def setUp(self):
        # Create a Reporter.
        self.r = Reporter.objects.create(first_name='John', last_name='Smith')

    def test_integrity_checks_on_creation(self):
        """
        Try to create a model instance that violates a FK constraint. If it
        fails it should fail with IntegrityError.
        """
        a1 = Article(headline="This is a test", pub_date=datetime.datetime(2005, 7, 27), reporter_id=30)
        try:
            a1.save()
        except IntegrityError:
            pass
        else:
            self.skipTest("This backend does not support integrity checks.")
        # Now that we know this backend supports integrity checks we make sure
        # constraints are also enforced for proxy  Refs #17519
        a2 = Article(
            headline='This is another test', reporter=self.r,
            pub_date=datetime.datetime(2012, 8, 3),
            reporter_proxy_id=30,
        )
        with self.assertRaises(IntegrityError):
            a2.save()

    def test_integrity_checks_on_update(self):
        """
        Try to update a model instance introducing a FK constraint violation.
        If it fails it should fail with IntegrityError.
        """
        # Create an Article.
        Article.objects.create(headline="Test article", pub_date=datetime.datetime(2010, 9, 4), reporter=self.r)
        # Retrieve it from the DB
        a1 = Article.objects.get(headline="Test article")
        a1.reporter_id = 30
        try:
            a1.save()
        except IntegrityError:
            pass
        else:
            self.skipTest("This backend does not support integrity checks.")
        # Now that we know this backend supports integrity checks we make sure
        # constraints are also enforced for proxy  Refs #17519
        # Create another article
        r_proxy = ReporterProxy.objects.get(pk=self.r.pk)
        Article.objects.create(
            headline='Another article',
            pub_date=datetime.datetime(1988, 5, 15),
            reporter=self.r, reporter_proxy=r_proxy,
        )
        # Retrieve the second article from the DB
        a2 = Article.objects.get(headline='Another article')
        a2.reporter_proxy_id = 30
        with self.assertRaises(IntegrityError):
            a2.save()

    def test_disable_constraint_checks_manually(self):
        """
        When constraint checks are disabled, should be able to write bad data
        without IntegrityErrors.
        """
        with transaction.atomic():
            # Create an Article.
            Article.objects.create(
                headline="Test article",
                pub_date=datetime.datetime(2010, 9, 4),
                reporter=self.r,
            )
            # Retrieve it from the DB
            a = Article.objects.get(headline="Test article")
            a.reporter_id = 30
            try:
                connection.disable_constraint_checking()
                a.save()
                connection.enable_constraint_checking()
            except IntegrityError:
                self.fail("IntegrityError should not have occurred.")
            transaction.set_rollback(True)

    def test_disable_constraint_checks_context_manager(self):
        """
        When constraint checks are disabled (using context manager), should be
        able to write bad data without IntegrityErrors.
        """
        with transaction.atomic():
            # Create an Article.
            Article.objects.create(
                headline="Test article",
                pub_date=datetime.datetime(2010, 9, 4),
                reporter=self.r,
            )
            # Retrieve it from the DB
            a = Article.objects.get(headline="Test article")
            a.reporter_id = 30
            try:
                with connection.constraint_checks_disabled():
                    a.save()
            except IntegrityError:
                self.fail("IntegrityError should not have occurred.")
            transaction.set_rollback(True)

    def test_check_constraints(self):
        """
        Constraint checks should raise an IntegrityError when bad data is in the DB.
        """
        with transaction.atomic():
            # Create an Article.
            Article.objects.create(
                headline="Test article",
                pub_date=datetime.datetime(2010, 9, 4),
                reporter=self.r,
            )
            # Retrieve it from the DB
            a = Article.objects.get(headline="Test article")
            a.reporter_id = 30
            with connection.constraint_checks_disabled():
                a.save()
                with self.assertRaises(IntegrityError):
                    connection.check_constraints()
            transaction.set_rollback(True)


class ThreadTests(TransactionTestCase):

    available_apps = ['backends']

    def test_default_connection_thread_local(self):
        """
        The default connection (i.e. django.db.connection) is different for
        each thread (#17258).
        """
        # Map connections by id because connections with identical aliases
        # have the same hash.
        connections_dict = {}
        connection.cursor()
        connections_dict[id(connection)] = connection

        def runner():
            # Passing django.db.connection between threads doesn't work while
            # connections[DEFAULT_DB_ALIAS] does.
            from django.db import connections
            connection = connections[DEFAULT_DB_ALIAS]
            # Allow thread sharing so the connection can be closed by the
            # main thread.
            connection.allow_thread_sharing = True
            connection.cursor()
            connections_dict[id(connection)] = connection
        for x in range(2):
            t = threading.Thread(target=runner)
            t.start()
            t.join()
        # Each created connection got different inner connection.
        self.assertEqual(
            len(set(conn.connection for conn in connections_dict.values())),
            3)
        # Finish by closing the connections opened by the other threads (the
        # connection opened in the main thread will automatically be closed on
        # teardown).
        for conn in connections_dict.values():
            if conn is not connection:
                conn.close()

    def test_connections_thread_local(self):
        """
        The connections are different for each thread (#17258).
        """
        # Map connections by id because connections with identical aliases
        # have the same hash.
        connections_dict = {}
        for conn in connections.all():
            connections_dict[id(conn)] = conn

        def runner():
            from django.db import connections
            for conn in connections.all():
                # Allow thread sharing so the connection can be closed by the
                # main thread.
                conn.allow_thread_sharing = True
                connections_dict[id(conn)] = conn
        for x in range(2):
            t = threading.Thread(target=runner)
            t.start()
            t.join()
        self.assertEqual(len(connections_dict), 6)
        # Finish by closing the connections opened by the other threads (the
        # connection opened in the main thread will automatically be closed on
        # teardown).
        for conn in connections_dict.values():
            if conn is not connection:
                conn.close()

    def test_pass_connection_between_threads(self):
        """
        A connection can be passed from one thread to the other (#17258).
        """
        Person.objects.create(first_name="John", last_name="Doe")

        def do_thread():
            def runner(main_thread_connection):
                from django.db import connections
                connections['default'] = main_thread_connection
                try:
                    Person.objects.get(first_name="John", last_name="Doe")
                except Exception as e:
                    exceptions.append(e)
            t = threading.Thread(target=runner, args=[connections['default']])
            t.start()
            t.join()

        # Without touching allow_thread_sharing, which should be False by default.
        exceptions = []
        do_thread()
        # Forbidden!
        self.assertIsInstance(exceptions[0], DatabaseError)

        # If explicitly setting allow_thread_sharing to False
        connections['default'].allow_thread_sharing = False
        exceptions = []
        do_thread()
        # Forbidden!
        self.assertIsInstance(exceptions[0], DatabaseError)

        # If explicitly setting allow_thread_sharing to True
        connections['default'].allow_thread_sharing = True
        exceptions = []
        do_thread()
        # All good
        self.assertEqual(exceptions, [])

    def test_closing_non_shared_connections(self):
        """
        A connection that is not explicitly shareable cannot be closed by
        another thread (#17258).
        """
        # First, without explicitly enabling the connection for sharing.
        exceptions = set()

        def runner1():
            def runner2(other_thread_connection):
                try:
                    other_thread_connection.close()
                except DatabaseError as e:
                    exceptions.add(e)
            t2 = threading.Thread(target=runner2, args=[connections['default']])
            t2.start()
            t2.join()
        t1 = threading.Thread(target=runner1)
        t1.start()
        t1.join()
        # The exception was raised
        self.assertEqual(len(exceptions), 1)

        # Then, with explicitly enabling the connection for sharing.
        exceptions = set()

        def runner1():
            def runner2(other_thread_connection):
                try:
                    other_thread_connection.close()
                except DatabaseError as e:
                    exceptions.add(e)
            # Enable thread sharing
            connections['default'].allow_thread_sharing = True
            t2 = threading.Thread(target=runner2, args=[connections['default']])
            t2.start()
            t2.join()
        t1 = threading.Thread(target=runner1)
        t1.start()
        t1.join()
        # No exception was raised
        self.assertEqual(len(exceptions), 0)


class MySQLPKZeroTests(TestCase):
    """
    Zero as id for AutoField should raise exception in MySQL, because MySQL
    does not allow zero for autoincrement primary key.
    """
    @skipIfDBFeature('allows_auto_pk_0')
    def test_zero_as_autoval(self):
        with self.assertRaises(ValueError):
            Square.objects.create(id=0, root=0, square=1)


class DBConstraintTestCase(TestCase):

    def test_can_reference_existent(self):
        obj = Object.objects.create()
        ref = ObjectReference.objects.create(obj=obj)
        self.assertEqual(ref.obj, obj)

        ref = ObjectReference.objects.get(obj=obj)
        self.assertEqual(ref.obj, obj)

    def test_can_reference_non_existent(self):
        self.assertFalse(Object.objects.filter(id=12345).exists())
        ref = ObjectReference.objects.create(obj_id=12345)
        ref_new = ObjectReference.objects.get(obj_id=12345)
        self.assertEqual(ref, ref_new)

        with self.assertRaises(Object.DoesNotExist):
            ref.obj

    def test_many_to_many(self):
        obj = Object.objects.create()
        obj.related_objects.create()
        self.assertEqual(Object.objects.count(), 2)
        self.assertEqual(obj.related_objects.count(), 1)

        intermediary_model = Object._meta.get_field("related_objects").remote_field.through
        intermediary_model.objects.create(from_object_id=obj.id, to_object_id=12345)
        self.assertEqual(obj.related_objects.count(), 1)
        self.assertEqual(intermediary_model.objects.count(), 2)


class BackendUtilTests(SimpleTestCase):

    def test_format_number(self):
        """
        Test the format_number converter utility
        """
        def equal(value, max_d, places, result):
            self.assertEqual(format_number(Decimal(value), max_d, places), result)

        equal('0', 12, 3,
              '0.000')
        equal('0', 12, 8,
              '0.00000000')
        equal('1', 12, 9,
              '1.000000000')
        equal('0.00000000', 12, 8,
              '0.00000000')
        equal('0.000000004', 12, 8,
              '0.00000000')
        equal('0.000000008', 12, 8,
              '0.00000001')
        equal('0.000000000000000000999', 10, 8,
              '0.00000000')
        equal('0.1234567890', 12, 10,
              '0.1234567890')
        equal('0.1234567890', 12, 9,
              '0.123456789')
        equal('0.1234567890', 12, 8,
              '0.12345679')
        equal('0.1234567890', 12, 5,
              '0.12346')
        equal('0.1234567890', 12, 3,
              '0.123')
        equal('0.1234567890', 12, 1,
              '0.1')
        equal('0.1234567890', 12, 0,
              '0')
        equal('0.1234567890', None, 0,
              '0')
        equal('1234567890.1234567890', None, 0,
              '1234567890')
        equal('1234567890.1234567890', None, 2,
              '1234567890.12')
        equal('0.1234', 5, None,
              '0.1234')
        equal('123.12', 5, None,
              '123.12')
        with self.assertRaises(Rounded):
            equal('0.1234567890', 5, None,
                  '0.12346')
        with self.assertRaises(Rounded):
            equal('1234567890.1234', 5, None,
                  '1234600000')


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite specific test.')
@skipUnlessDBFeature('can_share_in_memory_db')
class TestSqliteThreadSharing(TransactionTestCase):
    available_apps = ['backends']

    def test_database_sharing_in_threads(self):
        def create_object():
            Object.objects.create()

        create_object()

        thread = threading.Thread(target=create_object)
        thread.start()
        thread.join()

        self.assertEqual(Object.objects.count(), 2)
