from django.test import TestCase

from models import Simple


class InitialSQLTests(TestCase):
    def test_initial_sql(self):
        # The format of the included SQL file for this test suite is important.
        # It must end with a trailing newline in order to test the fix for #2161.

        # However, as pointed out by #14661, test data loaded by custom SQL
        # can't be relied upon; as a result, the test framework flushes the
        # data contents before every test. This test validates that this has
        # occurred.
        self.assertEqual(Simple.objects.count(), 0)
