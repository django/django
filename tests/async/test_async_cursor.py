from django.db import new_connection
from django.test import SimpleTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_async")
class AsyncCursorTests(SimpleTestCase):
    databases = {"default", "other"}

    async def test_aexecute(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute("SELECT 1")

    async def test_aexecutemany(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute("CREATE TABLE numbers (number SMALLINT)")
                await cursor.aexecutemany(
                    "INSERT INTO numbers VALUES (%s)", [(1,), (2,), (3,)]
                )
                await cursor.aexecute("SELECT * FROM numbers")
                result = await cursor.afetchall()
                self.assertEqual(result, [(1,), (2,), (3,)])

    async def test_afetchone(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute("SELECT 1")
                result = await cursor.afetchone()
            self.assertEqual(result, (1,))

    async def test_afetchmany(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute(
                    """
                    SELECT *
                    FROM (VALUES
                        ('BANANA'),
                        ('STRAWBERRY'),
                        ('MELON')
                    ) AS v (NAME)"""
                )
                result = await cursor.afetchmany(size=2)
            self.assertEqual(result, [("BANANA",), ("STRAWBERRY",)])

    async def test_afetchall(self):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute(
                    """
                    SELECT *
                    FROM (VALUES
                        ('BANANA'),
                        ('STRAWBERRY'),
                        ('MELON')
                    ) AS v (NAME)"""
                )
                result = await cursor.afetchall()
            self.assertEqual(result, [("BANANA",), ("STRAWBERRY",), ("MELON",)])

    async def test_aiter(self):
        result = []
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute(
                    """
                    SELECT *
                    FROM (VALUES
                        ('BANANA'),
                        ('STRAWBERRY'),
                        ('MELON')
                    ) AS v (NAME)"""
                )
                async for record in cursor:
                    result.append(record)
            self.assertEqual(result, [("BANANA",), ("STRAWBERRY",), ("MELON",)])

    async def test_acopy(self):
        result = []
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                async with cursor.acopy(
                    """
                    COPY (
                        SELECT *
                        FROM (VALUES
                            ('BANANA'),
                            ('STRAWBERRY'),
                            ('MELON')
                        ) AS v (NAME)
                    ) TO STDOUT"""
                ) as copy:
                    async for row in copy.rows():
                        result.append(row)
            self.assertEqual(result, [("BANANA",), ("STRAWBERRY",), ("MELON",)])

    async def test_astream(self):
        result = []
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                async for record in cursor.astream(
                    """
                    SELECT *
                    FROM (VALUES
                        ('BANANA'),
                        ('STRAWBERRY'),
                        ('MELON')
                    ) AS v (NAME)"""
                ):
                    result.append(record)
            self.assertEqual(result, [("BANANA",), ("STRAWBERRY",), ("MELON",)])

    async def test_ascroll(self):
        result = []
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute(
                    """
                    SELECT *
                    FROM (VALUES
                        ('BANANA'),
                        ('STRAWBERRY'),
                        ('MELON')
                    ) AS v (NAME)"""
                )
                await cursor.ascroll(1, "absolute")

                result = await cursor.afetchall()
                self.assertEqual(result, [("STRAWBERRY",), ("MELON",)])
                await cursor.ascroll(0, "absolute")
                result = await cursor.afetchall()
                self.assertEqual(result, [("BANANA",), ("STRAWBERRY",), ("MELON",)])
