# -*- coding: utf-8 -*-
# Unit and doctests for specific database backends.
from __future__ import with_statement, absolute_import

import datetime
import threading

from django.conf import settings
from django.core.management.color import no_style
from django.core.exceptions import ImproperlyConfigured
from django.db import (backend, connection, connections, DEFAULT_DB_ALIAS,
    IntegrityError, transaction)
from django.db.backends.signals import connection_created
from django.db.backends.postgresql_psycopg2 import version as pg_version
from django.db.utils import ConnectionHandler, DatabaseError, load_backend
from django.test import TestCase, skipUnlessDBFeature, TransactionTestCase
from django.test.utils import override_settings
from django.utils import unittest

from . import models


class OracleChecks(unittest.TestCase):

    @unittest.skipUnless(connection.vendor == 'oracle',
                         "No need to check Oracle cursor semantics")
    def test_dbms_session(self):
        # If the backend is Oracle, test that we can call a standard
        # stored procedure through our cursor wrapper.
        convert_unicode = backend.convert_unicode
        cursor = connection.cursor()
        cursor.callproc(convert_unicode('DBMS_SESSION.SET_IDENTIFIER'),
                        [convert_unicode('_django_testing!'),])

    @unittest.skipUnless(connection.vendor == 'oracle',
                         "No need to check Oracle cursor semantics")
    def test_cursor_var(self):
        # If the backend is Oracle, test that we can pass cursor variables
        # as query parameters.
        cursor = connection.cursor()
        var = cursor.var(backend.Database.STRING)
        cursor.execute("BEGIN %s := 'X'; END; ", [var])
        self.assertEqual(var.getvalue(), 'X')

    @unittest.skipUnless(connection.vendor == 'oracle',
                         "No need to check Oracle cursor semantics")
    def test_long_string(self):
        # If the backend is Oracle, test that we can save a text longer
        # than 4000 chars and read it properly
        c = connection.cursor()
        c.execute('CREATE TABLE ltext ("TEXT" NCLOB)')
        long_str = ''.join([unicode(x) for x in xrange(4000)])
        c.execute('INSERT INTO ltext VALUES (%s)',[long_str])
        c.execute('SELECT text FROM ltext')
        row = c.fetchone()
        self.assertEqual(long_str, row[0].read())
        c.execute('DROP TABLE ltext')

    @unittest.skipUnless(connection.vendor == 'oracle',
                         "No need to check Oracle connection semantics")
    def test_client_encoding(self):
        # If the backend is Oracle, test that the client encoding is set
        # correctly.  This was broken under Cygwin prior to r14781.
        c = connection.cursor()  # Ensure the connection is initialized.
        self.assertEqual(connection.connection.encoding, "UTF-8")
        self.assertEqual(connection.connection.nencoding, "UTF-8")

class MySQLTests(TestCase):
    @unittest.skipUnless(connection.vendor == 'mysql',
                        "Test valid only for MySQL")
    def test_server_version_connections(self):
        connection.close()
        connection.get_server_version()
        self.assertTrue(connection.connection is None)

class DateQuotingTest(TestCase):

    def test_django_date_trunc(self):
        """
        Test the custom ``django_date_trunc method``, in particular against
        fields which clash with strings passed to it (e.g. 'year') - see
        #12818__.

        __: http://code.djangoproject.com/ticket/12818

        """
        updated = datetime.datetime(2010, 2, 20)
        models.SchoolClass.objects.create(year=2009, last_updated=updated)
        years = models.SchoolClass.objects.dates('last_updated', 'year')
        self.assertEqual(list(years), [datetime.datetime(2010, 1, 1, 0, 0)])

    def test_django_extract(self):
        """
        Test the custom ``django_extract method``, in particular against fields
        which clash with strings passed to it (e.g. 'day') - see #12818__.

        __: http://code.djangoproject.com/ticket/12818

        """
        updated = datetime.datetime(2010, 2, 20)
        models.SchoolClass.objects.create(year=2009, last_updated=updated)
        classes = models.SchoolClass.objects.filter(last_updated__day=20)
        self.assertEqual(len(classes), 1)

class LastExecutedQueryTest(TestCase):

    def setUp(self):
        # connection.queries will not be filled in without this
        settings.DEBUG = True

    def tearDown(self):
        settings.DEBUG = False

    # There are no tests for the sqlite backend because it does not
    # implement paramater escaping. See #14091.

    @unittest.skipUnless(connection.vendor in ('oracle', 'postgresql'),
                         "These backends use the standard parameter escaping rules")
    def test_parameter_escaping(self):
        # check that both numbers and string are properly quoted
        list(models.Tag.objects.filter(name="special:\\\"':", object_id=12))
        sql = connection.queries[-1]['sql']
        self.assertTrue("= 'special:\\\"'':' " in sql)
        self.assertTrue("= 12 " in sql)

    @unittest.skipUnless(connection.vendor == 'mysql',
                         "MySQL uses backslashes to escape parameters.")
    def test_parameter_escaping(self):
        list(models.Tag.objects.filter(name="special:\\\"':", object_id=12))
        sql = connection.queries[-1]['sql']
        # only this line is different from the test above
        self.assertTrue("= 'special:\\\\\\\"\\':' " in sql)
        self.assertTrue("= 12 " in sql)

class ParameterHandlingTest(TestCase):
    def test_bad_parameter_count(self):
        "An executemany call with too many/not enough parameters will raise an exception (Refs #12612)"
        cursor = connection.cursor()
        query = ('INSERT INTO %s (%s, %s) VALUES (%%s, %%s)' % (
            connection.introspection.table_name_converter('backends_square'),
            connection.ops.quote_name('root'),
            connection.ops.quote_name('square')
        ))
        self.assertRaises(Exception, cursor.executemany, query, [(1,2,3),])
        self.assertRaises(Exception, cursor.executemany, query, [(1,),])

# Unfortunately, the following tests would be a good test to run on all
# backends, but it breaks MySQL hard. Until #13711 is fixed, it can't be run
# everywhere (although it would be an effective test of #13711).
class LongNameTest(TestCase):
    """Long primary keys and model names can result in a sequence name
    that exceeds the database limits, which will result in truncation
    on certain databases (e.g., Postgres). The backend needs to use
    the correct sequence name in last_insert_id and other places, so
    check it is. Refs #8901.
    """

    @skipUnlessDBFeature('supports_long_model_names')
    def test_sequence_name_length_limits_create(self):
        """Test creation of model with long name and long pk name doesn't error. Ref #8901"""
        models.VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ.objects.create()

    @skipUnlessDBFeature('supports_long_model_names')
    def test_sequence_name_length_limits_m2m(self):
        """Test an m2m save of a model with a long name and a long m2m field name doesn't error as on Django >=1.2 this now uses object saves. Ref #8901"""
        obj = models.VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ.objects.create()
        rel_obj = models.Person.objects.create(first_name='Django', last_name='Reinhardt')
        obj.m2m_also_quite_long_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz.add(rel_obj)

    @skipUnlessDBFeature('supports_long_model_names')
    def test_sequence_name_length_limits_flush(self):
        """Test that sequence resetting as part of a flush with model with long name and long pk name doesn't error. Ref #8901"""
        # A full flush is expensive to the full test, so we dig into the
        # internals to generate the likely offending SQL and run it manually

        # Some convenience aliases
        VLM = models.VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
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
        models.Post.objects.create(id=10, name='1st post', text='hello world')

        # Reset the sequences for the database
        cursor = connection.cursor()
        commands = connections[DEFAULT_DB_ALIAS].ops.sequence_reset_sql(no_style(), [models.Post])
        for sql in commands:
            cursor.execute(sql)

        # If we create a new object now, it should have a PK greater
        # than the PK we specified manually.
        obj = models.Post.objects.create(name='New post', text='goodbye world')
        self.assertTrue(obj.pk > 10)

class PostgresVersionTest(TestCase):
    def assert_parses(self, version_string, version):
        self.assertEqual(pg_version._parse_version(version_string), version)

    def test_parsing(self):
        """Test PostgreSQL version parsing from `SELECT version()` output"""
        self.assert_parses("PostgreSQL 8.3 beta4", 80300)
        self.assert_parses("PostgreSQL 8.3", 80300)
        self.assert_parses("EnterpriseDB 8.3", 80300)
        self.assert_parses("PostgreSQL 8.3.6", 80306)
        self.assert_parses("PostgreSQL 8.4beta1", 80400)
        self.assert_parses("PostgreSQL 8.3.1 on i386-apple-darwin9.2.2, compiled by GCC i686-apple-darwin9-gcc-4.0.1 (GCC) 4.0.1 (Apple Inc. build 5478)", 80301)

    def test_version_detection(self):
        """Test PostgreSQL version detection"""

        # Helper mocks
        class CursorMock(object):
            "Very simple mock of DB-API cursor"
            def execute(self, arg):
                pass

            def fetchone(self):
                return ["PostgreSQL 8.3"]

        class OlderConnectionMock(object):
            "Mock of psycopg2 (< 2.0.12) connection"
            def cursor(self):
                return CursorMock()

        # psycopg2 < 2.0.12 code path
        conn = OlderConnectionMock()
        self.assertEqual(pg_version.get_version(conn), 80300)

class PostgresNewConnectionTest(TestCase):
    """
    #17062: PostgreSQL shouldn't roll back SET TIME ZONE, even if the first
    transaction is rolled back.
    """
    @unittest.skipUnless(
        connection.vendor == 'postgresql' and connection.isolation_level > 0,
        "This test applies only to PostgreSQL without autocommit")
    def test_connect_and_rollback(self):
        new_connections = ConnectionHandler(settings.DATABASES)
        new_connection = new_connections[DEFAULT_DB_ALIAS]
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

            # Fetch a new connection with the new_tz as default
            # time zone, run a query and rollback.
            new_connection.settings_dict['TIME_ZONE'] = new_tz
            new_connection.enter_transaction_management()
            cursor = new_connection.cursor()
            new_connection.rollback()

            # Now let's see if the rollback rolled back the SET TIME ZONE.
            cursor.execute("SHOW TIMEZONE")
            tz = cursor.fetchone()[0]
            self.assertEqual(new_tz, tz)
        finally:
            try:
                new_connection.close()
            except DatabaseError:
                pass


# Unfortunately with sqlite3 the in-memory test database cannot be
# closed, and so it cannot be re-opened during testing, and so we
# sadly disable this test for now.
class ConnectionCreatedSignalTest(TestCase):
    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_signal(self):
        data = {}
        def receiver(sender, connection, **kwargs):
            data["connection"] = connection

        connection_created.connect(receiver)
        connection.close()
        cursor = connection.cursor()
        self.assertTrue(data["connection"].connection is connection.connection)

        connection_created.disconnect(receiver)
        data.clear()
        cursor = connection.cursor()
        self.assertTrue(data == {})


class EscapingChecks(TestCase):

    @unittest.skipUnless(connection.vendor == 'sqlite',
                         "This is a sqlite-specific issue")
    def test_parameter_escaping(self):
        #13648: '%s' escaping support for sqlite3
        cursor = connection.cursor()
        response = cursor.execute(
            "select strftime('%%s', date('now'))").fetchall()[0][0]
        self.assertNotEqual(response, None)
        # response should be an non-zero integer
        self.assertTrue(int(response))


class BackendTestCase(TestCase):

    def create_squares_with_executemany(self, args):
        cursor = connection.cursor()
        opts = models.Square._meta
        tbl = connection.introspection.table_name_converter(opts.db_table)
        f1 = connection.ops.quote_name(opts.get_field('root').column)
        f2 = connection.ops.quote_name(opts.get_field('square').column)
        query = 'INSERT INTO %s (%s, %s) VALUES (%%s, %%s)' % (tbl, f1, f2)
        cursor.executemany(query, args)

    def test_cursor_executemany(self):
        #4896: Test cursor.executemany
        args = [(i, i**2) for i in range(-5, 6)]
        self.create_squares_with_executemany(args)
        self.assertEqual(models.Square.objects.count(), 11)
        for i in range(-5, 6):
            square = models.Square.objects.get(root=i)
            self.assertEqual(square.square, i**2)

    def test_cursor_executemany_with_empty_params_list(self):
        #4765: executemany with params=[] does nothing
        args = []
        self.create_squares_with_executemany(args)
        self.assertEqual(models.Square.objects.count(), 0)

    def test_cursor_executemany_with_iterator(self):
        #10320: executemany accepts iterators
        args = iter((i, i**2) for i in range(-3, 2))
        self.create_squares_with_executemany(args)
        self.assertEqual(models.Square.objects.count(), 5)

        args = iter((i, i**2) for i in range(3, 7))
        with override_settings(DEBUG=True):
            # same test for DebugCursorWrapper
            self.create_squares_with_executemany(args)
        self.assertEqual(models.Square.objects.count(), 9)


    def test_unicode_fetches(self):
        #6254: fetchone, fetchmany, fetchall return strings as unicode objects
        qn = connection.ops.quote_name
        models.Person(first_name="John", last_name="Doe").save()
        models.Person(first_name="Jane", last_name="Doe").save()
        models.Person(first_name="Mary", last_name="Agnelline").save()
        models.Person(first_name="Peter", last_name="Parker").save()
        models.Person(first_name="Clark", last_name="Kent").save()
        opts2 = models.Person._meta
        f3, f4 = opts2.get_field('first_name'), opts2.get_field('last_name')
        query2 = ('SELECT %s, %s FROM %s ORDER BY %s'
          % (qn(f3.column), qn(f4.column), connection.introspection.table_name_converter(opts2.db_table),
             qn(f3.column)))
        cursor = connection.cursor()
        cursor.execute(query2)
        self.assertEqual(cursor.fetchone(), (u'Clark', u'Kent'))
        self.assertEqual(list(cursor.fetchmany(2)), [(u'Jane', u'Doe'), (u'John', u'Doe')])
        self.assertEqual(list(cursor.fetchall()), [(u'Mary', u'Agnelline'), (u'Peter', u'Parker')])

    def test_database_operations_helper_class(self):
        # Ticket #13630
        self.assertTrue(hasattr(connection, 'ops'))
        self.assertTrue(hasattr(connection.ops, 'connection'))
        self.assertEqual(connection, connection.ops.connection)

    def test_duplicate_table_error(self):
        """ Test that creating an existing table returns a DatabaseError """
        cursor = connection.cursor()
        query = 'CREATE TABLE %s (id INTEGER);' % models.Article._meta.db_table
        with self.assertRaises(DatabaseError):
            cursor.execute(query)

# We don't make these tests conditional because that means we would need to
# check and differentiate between:
# * MySQL+InnoDB, MySQL+MYISAM (something we currently can't do).
# * if sqlite3 (if/once we get #14204 fixed) has referential integrity turned
#   on or not, something that would be controlled by runtime support and user
#   preference.
# verify if its type is django.database.db.IntegrityError.

class FkConstraintsTests(TransactionTestCase):

    def setUp(self):
        # Create a Reporter.
        self.r = models.Reporter.objects.create(first_name='John', last_name='Smith')

    def test_integrity_checks_on_creation(self):
        """
        Try to create a model instance that violates a FK constraint. If it
        fails it should fail with IntegrityError.
        """
        a = models.Article(headline="This is a test", pub_date=datetime.datetime(2005, 7, 27), reporter_id=30)
        try:
            a.save()
        except IntegrityError:
            return
        self.skipTest("This backend does not support integrity checks.")

    def test_integrity_checks_on_update(self):
        """
        Try to update a model instance introducing a FK constraint violation.
        If it fails it should fail with IntegrityError.
        """
        # Create an Article.
        models.Article.objects.create(headline="Test article", pub_date=datetime.datetime(2010, 9, 4), reporter=self.r)
        # Retrive it from the DB
        a = models.Article.objects.get(headline="Test article")
        a.reporter_id = 30
        try:
            a.save()
        except IntegrityError:
            return
        self.skipTest("This backend does not support integrity checks.")

    def test_disable_constraint_checks_manually(self):
        """
        When constraint checks are disabled, should be able to write bad data without IntegrityErrors.
        """
        with transaction.commit_manually():
            # Create an Article.
            models.Article.objects.create(headline="Test article", pub_date=datetime.datetime(2010, 9, 4), reporter=self.r)
            # Retrive it from the DB
            a = models.Article.objects.get(headline="Test article")
            a.reporter_id = 30
            try:
                connection.disable_constraint_checking()
                a.save()
                connection.enable_constraint_checking()
            except IntegrityError:
                self.fail("IntegrityError should not have occurred.")
            finally:
                transaction.rollback()

    def test_disable_constraint_checks_context_manager(self):
        """
        When constraint checks are disabled (using context manager), should be able to write bad data without IntegrityErrors.
        """
        with transaction.commit_manually():
            # Create an Article.
            models.Article.objects.create(headline="Test article", pub_date=datetime.datetime(2010, 9, 4), reporter=self.r)
            # Retrive it from the DB
            a = models.Article.objects.get(headline="Test article")
            a.reporter_id = 30
            try:
                with connection.constraint_checks_disabled():
                    a.save()
            except IntegrityError:
                self.fail("IntegrityError should not have occurred.")
            finally:
                transaction.rollback()

    def test_check_constraints(self):
        """
        Constraint checks should raise an IntegrityError when bad data is in the DB.
        """
        with transaction.commit_manually():
            # Create an Article.
            models.Article.objects.create(headline="Test article", pub_date=datetime.datetime(2010, 9, 4), reporter=self.r)
            # Retrive it from the DB
            a = models.Article.objects.get(headline="Test article")
            a.reporter_id = 30
            try:
                with connection.constraint_checks_disabled():
                    a.save()
                    with self.assertRaises(IntegrityError):
                        connection.check_constraints()
            finally:
                transaction.rollback()


class ThreadTests(TestCase):

    def test_default_connection_thread_local(self):
        """
        Ensure that the default connection (i.e. django.db.connection) is
        different for each thread.
        Refs #17258.
        """
        connections_set = set()
        connection.cursor()
        connections_set.add(connection.connection)
        def runner():
            from django.db import connection
            connection.cursor()
            connections_set.add(connection.connection)
        for x in xrange(2):
            t = threading.Thread(target=runner)
            t.start()
            t.join()
        self.assertEquals(len(connections_set), 3)
        # Finish by closing the connections opened by the other threads (the
        # connection opened in the main thread will automatically be closed on
        # teardown).
        for conn in connections_set:
            if conn != connection.connection:
                conn.close()

    def test_connections_thread_local(self):
        """
        Ensure that the connections are different for each thread.
        Refs #17258.
        """
        connections_set = set()
        for conn in connections.all():
            connections_set.add(conn)
        def runner():
            from django.db import connections
            for conn in connections.all():
                # Allow thread sharing so the connection can be closed by the
                # main thread.
                conn.allow_thread_sharing = True
                connections_set.add(conn)
        for x in xrange(2):
            t = threading.Thread(target=runner)
            t.start()
            t.join()
        self.assertEquals(len(connections_set), 6)
        # Finish by closing the connections opened by the other threads (the
        # connection opened in the main thread will automatically be closed on
        # teardown).
        for conn in connections_set:
            if conn != connection:
                conn.close()

    def test_pass_connection_between_threads(self):
        """
        Ensure that a connection can be passed from one thread to the other.
        Refs #17258.
        """
        models.Person.objects.create(first_name="John", last_name="Doe")

        def do_thread():
            def runner(main_thread_connection):
                from django.db import connections
                connections['default'] = main_thread_connection
                try:
                    models.Person.objects.get(first_name="John", last_name="Doe")
                except DatabaseError, e:
                    exceptions.append(e)
            t = threading.Thread(target=runner, args=[connections['default']])
            t.start()
            t.join()

        # Without touching allow_thread_sharing, which should be False by default.
        exceptions = []
        do_thread()
        # Forbidden!
        self.assertTrue(isinstance(exceptions[0], DatabaseError))

        # If explicitly setting allow_thread_sharing to False
        connections['default'].allow_thread_sharing = False
        exceptions = []
        do_thread()
        # Forbidden!
        self.assertTrue(isinstance(exceptions[0], DatabaseError))

        # If explicitly setting allow_thread_sharing to True
        connections['default'].allow_thread_sharing = True
        exceptions = []
        do_thread()
        # All good
        self.assertEqual(len(exceptions), 0)

    def test_closing_non_shared_connections(self):
        """
        Ensure that a connection that is not explicitly shareable cannot be
        closed by another thread.
        Refs #17258.
        """
        # First, without explicitly enabling the connection for sharing.
        exceptions = set()
        def runner1():
            def runner2(other_thread_connection):
                try:
                    other_thread_connection.close()
                except DatabaseError, e:
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
                except DatabaseError, e:
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


class BackendLoadingTests(TestCase):
    def test_old_style_backends_raise_useful_exception(self):
        self.assertRaisesRegexp(ImproperlyConfigured,
            "Try using django.db.backends.sqlite3 instead",
            load_backend, 'sqlite3')
