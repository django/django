from unittest.mock import MagicMock

from django.db import DEFAULT_DB_ALIAS, async_connections
from django.test import AsyncTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_async")
class AsyncCursorTest(AsyncTestCase):

    @classmethod
    async def asyncSetUpTestData(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE test_table_tmp (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    async def test_execute(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO test_table_tmp (name) VALUES ('1');
            """)
            res = await cursor.execute("""SELECT name FROM test_table_tmp;""")

            self.assertEqual(await res.fetchone(), ('1', ))

    async def test_executemany(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            await cursor.executemany(
                "INSERT INTO test_table_tmp (name) VALUES (%s)",
                [(1, ), (2, )]
            )
            res = await cursor.execute("""SELECT name FROM test_table_tmp;""")

            self.assertEqual(await res.fetchall(), [('1', ), ('2', )])

    async def test_iterator(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO test_table_tmp (name) VALUES ('1'), ('2'), ('3');
            """)
            await cursor.execute("""SELECT name FROM test_table_tmp;""")

            self.assertEqual(
                [i async for i in  cursor],
                [('1', ), ('2', ), ('3',)]
            )

    async def test_execution_wrapper(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        wrapper_spy = MagicMock()

        def test_wrapper(execute, sql, params, many, context):
            wrapper_spy(sql=sql, params=params, many=many)
            return execute(sql, params, many, context)

        with connection.execute_wrapper(test_wrapper):
            async with connection.cursor() as cursor:
                await cursor.execute("""select 1""")

        wrapper_spy.assert_called_once_with(sql='select 1', params=None, many=False)
