import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class PostgreSQLTestCase(TestCase):
    pass
