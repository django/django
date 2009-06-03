from django.conf import settings
from django.db import connections
from django.test import TestCase

from models import Book

class DatabaseSettingTestCase(TestCase):
    def setUp(self):
        settings.DATABASES['__test_db'] = {
            'DATABASE_ENGINE': 'sqlite3',
            'DATABASE_NAME': ':memory:',
        }

    def tearDown(self):
        del settings.DATABASES['__test_db']

    def test_db_connection(self):
        connections['default'].cursor()
        connections['__test_db'].cursor()

class ConnectionTestCase(TestCase):
    def test_queries(self):
        for connection in connections.all():
            qn = connection.ops.quote_name
            cursor = connection.cursor()
            cursor.execute("""INSERT INTO %(table)s (%(col)s) VALUES (%%s)""" % {
                'table': qn(Book._meta.db_table),
                'col': qn(Book._meta.get_field_by_name('title')[0].column),
            }, ('Dive Into Python',))

        for connection in connections.all():
            qn = connection.ops.quote_name
            cursor = connection.cursor()
            cursor.execute("""SELECT * FROM %(table)s""" % {'table': qn(Book._meta.db_table)})
            data = cursor.fetchall()
            self.assertEqual('Dive Into Python', data[0][1])
