from django.core.management.color import no_style
from django.core.management.sql import custom_sql_for_model
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import TestCase

from .models import Simple


class InitialSQLTests(TestCase):
    # The format of the included SQL file for this test suite is important.
    # It must end with a trailing newline in order to test the fix for #2161.

    def test_initial_sql(self):
        # As pointed out by #14661, test data loaded by custom SQL
        # can't be relied upon; as a result, the test framework flushes the
        # data contents before every test. This test validates that this has
        # occurred.
        self.assertEqual(Simple.objects.count(), 0)

    def test_custom_sql(self):
        # Simulate the custom SQL loading by syncdb
        connection = connections[DEFAULT_DB_ALIAS]
        custom_sql = custom_sql_for_model(Simple, no_style(), connection)
        self.assertEqual(len(custom_sql), 8)
        cursor = connection.cursor()
        for sql in custom_sql:
            cursor.execute(sql)
        self.assertEqual(Simple.objects.count(), 8)
