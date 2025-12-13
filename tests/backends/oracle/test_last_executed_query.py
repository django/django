from django.db import connection
from django.test import TestCase
from django.test.utils import skipUnless


@skipUnless(connection.vendor == "oracle", "Oracle-specific tests")
class TestLastExecutedQueryFallback(TestCase):
    def test_last_executed_query_fallback(self):
        # Use a real Oracle cursor and force an error
        with connection.cursor() as cursor:
            sql = "INVALID SQL"
            params = []
            try:
                cursor.execute(sql, params)
            except Exception:
                pass

            # The result MUST NOT be None and MUST fall back to the SQL string
            result = connection.ops.last_executed_query(cursor, sql, params)
            self.assertIsNotNone(result)
            self.assertEqual(result, sql)
