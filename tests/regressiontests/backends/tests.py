# -*- coding: utf-8 -*-
# Unit and doctests for specific database backends.
import datetime
import unittest

from django.conf import settings
from django.db import backend, connection, DEFAULT_DB_ALIAS, IntegrityError
from django.db.backends.signals import connection_created
from django.db.backends.postgresql import version as pg_version
from django.test import TestCase, TransactionTestCase

import models

class OracleChecks(unittest.TestCase):

    def test_dbms_session(self):
        # If the backend is Oracle, test that we can call a standard
        # stored procedure through our cursor wrapper.
        if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.oracle':
            convert_unicode = backend.convert_unicode
            cursor = connection.cursor()
            cursor.callproc(convert_unicode('DBMS_SESSION.SET_IDENTIFIER'),
                            [convert_unicode('_django_testing!'),])
            return True
        else:
            return True

    def test_cursor_var(self):
        # If the backend is Oracle, test that we can pass cursor variables
        # as query parameters.
        if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.oracle':
            cursor = connection.cursor()
            var = cursor.var(backend.Database.STRING)
            cursor.execute("BEGIN %s := 'X'; END; ", [var])
            self.assertEqual(var.getvalue(), 'X')

    def test_long_string(self):
        # If the backend is Oracle, test that we can save a text longer
        # than 4000 chars and read it properly
        if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.oracle':
            c = connection.cursor()
            c.execute('CREATE TABLE ltext ("TEXT" NCLOB)')
            long_str = ''.join([unicode(x) for x in xrange(4000)])
            c.execute('INSERT INTO ltext VALUES (%s)',[long_str])
            c.execute('SELECT text FROM ltext')
            row = c.fetchone()
            self.assertEquals(long_str, row[0].read())
            c.execute('DROP TABLE ltext')

    def test_client_encoding(self):
        # If the backend is Oracle, test that the client encoding is set
        # correctly.  This was broken under Cygwin prior to r14781.
        if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.oracle':
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
if settings.DATABASES[DEFAULT_DB_ALIAS]["ENGINE"] != "django.db.backends.sqlite3":
    class ConnectionCreatedSignalTest(TestCase):
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
