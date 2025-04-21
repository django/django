from django.db import async_connections, DEFAULT_DB_ALIAS
from django.test import TestCase
from django.test import skipUnlessDBFeature

# todo: error with thread local (forbidden create if no async)

@skipUnlessDBFeature("supports_async")
class AsyncConnectionsTest(TestCase):

    async def test_success(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            res = await cursor.execute("""select 1""")
            data = await res.fetchone()

            self.assertEqual(data[0], 1)
