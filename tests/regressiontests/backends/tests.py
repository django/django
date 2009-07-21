# -*- coding: utf-8 -*-

# Unit tests for specific database backends.

import unittest

from django.db import connection
from django.conf import settings


class Callproc(unittest.TestCase):

    def test_dbms_session(self):
        # If the backend is Oracle, test that we can call a standard
        # stored procedure through our cursor wrapper.
        if settings.DATABASE_ENGINE == 'oracle':
            cursor = connection.cursor()
            cursor.callproc('DBMS_SESSION.SET_IDENTIFIER',
                            ['_django_testing!',])
            return True
        else:
            return True
            
class LongString(unittest.TestCase):

    def test_long_string(self):
        # If the backend is Oracle, test that we can save a text longer
        # than 4000 chars and read it properly
        if settings.DATABASE_ENGINE == 'oracle':
            c = connection.cursor()
            c.execute('CREATE TABLE ltext ("TEXT" NCLOB)')
            long_str = ''.join([unicode(x) for x in xrange(4000)])
            c.execute('INSERT INTO ltext VALUES (%s)',[long_str])
            c.execute('SELECT text FROM ltext')
            row = c.fetchone()
            c.execute('DROP TABLE ltext')
            self.assertEquals(long_str, row[0].read())

if __name__ == '__main__':
    unittest.main()
