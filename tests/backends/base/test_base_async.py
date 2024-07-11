import unittest

from django.db import connection, new_connection
from django.test import SimpleTestCase


@unittest.skipUnless(connection.supports_async is True, "Async DB test")
class AsyncDatabaseWrapperTests(SimpleTestCase):
    async def test_async_cursor(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.execute("SELECT 1")
                result = (await cursor.fetchone())[0]
            self.assertEqual(result, 1)

    async def test_async_cursor_alias(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute("SELECT 1")
                result = (await cursor.afetchone())[0]
            self.assertEqual(result, 1)
