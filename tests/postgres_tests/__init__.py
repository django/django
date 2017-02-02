import unittest

from django.db import connection
from django.db.backends.signals import connection_created
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class PostgreSQLTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # No need to keep that signal overhead for non PostgreSQL-related tests.
        from django.contrib.postgres.signals import register_hstore_handler

        connection_created.disconnect(register_hstore_handler)
        super().tearDownClass()
