from itertools import chain

from django.db.backends.base.operations import BaseAsyncDatabaseOperations
from django.db.backends.sqlite3.operations import (
    DatabaseOperations as SQLiteDatabaseOperations,
)
from django.utils.functional import cached_property
from django.utils.functools import alru_cache


class DatabaseOperations(SQLiteDatabaseOperations, BaseAsyncDatabaseOperations):
    async def fetch_returned_insert_rows(self, cursor):
        """
        Given a cursor object that has just performed an INSERT...RETURNING
        statement into a table, return the list of returned data.
        """
        return await cursor.fetchall()

    async def _quote_params_for_last_executed_query(self, params):
        BATCH_SIZE = 999
        if len(params) > BATCH_SIZE:
            results = ()
            for index in range(0, len(params), BATCH_SIZE):
                chunk = params[index:index + BATCH_SIZE]
                results += await self._quote_params_for_last_executed_query(chunk)
            return results

        sql = 'SELECT ' + ', '.join(['QUOTE(?)'] * len(params))
        # Bypass Django's wrappers and use the underlying sqlite3 connection
        # to avoid logging this query - it would trigger infinite recursion.
        cursor = await self.connection.connection.cursor()
        # Native sqlite3 cursors cannot be used as context managers.
        try:
            await cursor.execute(sql, params)
            return await cursor.fetchone()
        finally:
            await cursor.close()

    async def last_executed_query(self, cursor, sql, params):
        if params:
            if isinstance(params, (list, tuple)):
                params = await self._quote_params_for_last_executed_query(params)
            else:
                values = tuple(params.values())
                values = await self._quote_params_for_last_executed_query(values)
                params = dict(zip(params, values))
            return sql % params
        else:
            return sql

    async def __references_graph(self, table_name):
        query = """
        WITH tables AS (
            SELECT %s name
            UNION
            SELECT sqlite_master.name
            FROM sqlite_master
            JOIN tables ON (sql REGEXP %s || tables.name || %s)
        ) SELECT name FROM tables;
        """
        params = (
            table_name,
            r'(?i)\s+references\s+("|\')?',
            r'("|\')?\s*\(',
        )
        with await self.connection.cursor() as cursor:
            results = await cursor.execute(query, params)
            return [row[0] for row in await results.fetchall()]

    @cached_property
    def _references_graph(self):
        return alru_cache(maxsize=512)(self.__references_graph)

    async def sql_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        if tables and allow_cascade:
            # Simulate TRUNCATE CASCADE by recursively collecting the tables
            # referencing the tables to be flushed.
            tables = set(chain.from_iterable(await self._references_graph(table) for table in tables))
        sql = ['%s %s %s;' % (
            style.SQL_KEYWORD('DELETE'),
            style.SQL_KEYWORD('FROM'),
            style.SQL_FIELD(self.quote_name(table))
        ) for table in tables]
        if reset_sequences:
            sequences = [{'table': table} for table in tables]
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
        return sql
