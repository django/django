from django.db import DEFAULT_DB_ALIAS, async_connections
from django.test import AsyncTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_async")
class AsyncConnectionsTest(AsyncTestCase):

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

    async def test_success(self):
        connection = async_connections[DEFAULT_DB_ALIAS]

        async with connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO test_table_tmp (name) VALUES ('Test Name');
            """)
            res = await cursor.execute("""SELECT * FROM test_table_tmp;""")
            data = await res.fetchone()

