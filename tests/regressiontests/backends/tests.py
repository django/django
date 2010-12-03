# -*- coding: utf-8 -*-
# Unit and doctests for specific database backends.
import datetime

from django.core.management.color import no_style
from django.db import backend, connection, connections, DEFAULT_DB_ALIAS, IntegrityError
from django.db.backends.signals import connection_created
from django.db.backends.postgresql import version as pg_version
from django.test import TestCase, skipUnlessDBFeature, TransactionTestCase
from django.utils import unittest

from regressiontests.backends import models

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
        self.assert_parses("PostgreSQL 8.3 beta4", (8, 3, None))
        self.assert_parses("PostgreSQL 8.3", (8, 3, None))
        self.assert_parses("EnterpriseDB 8.3", (8, 3, None))
        self.assert_parses("PostgreSQL 8.3.6", (8, 3, 6))
        self.assert_parses("PostgreSQL 8.4beta1", (8, 4, None))
        self.assert_parses("PostgreSQL 8.3.1 on i386-apple-darwin9.2.2, compiled by GCC i686-apple-darwin9-gcc-4.0.1 (GCC) 4.0.1 (Apple Inc. build 5478)", (8, 3, 1))

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
        self.assertTrue(data["connection"] is connection)

        connection_created.disconnect(receiver)
        data.clear()
        cursor = connection.cursor()
        self.assertTrue(data == {})


class BackendTestCase(TestCase):
    def test_cursor_executemany(self):
        #4896: Test cursor.executemany
        cursor = connection.cursor()
        qn = connection.ops.quote_name
        opts = models.Square._meta
        f1, f2 = opts.get_field('root'), opts.get_field('square')
        query = ('INSERT INTO %s (%s, %s) VALUES (%%s, %%s)'
                 % (connection.introspection.table_name_converter(opts.db_table), qn(f1.column), qn(f2.column)))
        cursor.executemany(query, [(i, i**2) for i in range(-5, 6)])
        self.assertEqual(models.Square.objects.count(), 11)
        for i in range(-5, 6):
            square = models.Square.objects.get(root=i)
            self.assertEqual(square.square, i**2)

        #4765: executemany with params=[] does nothing
        cursor.executemany(query, [])
        self.assertEqual(models.Square.objects.count(), 11)

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
            pass

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
            pass
