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


if __name__ == '__main__':
    unittest.main()
