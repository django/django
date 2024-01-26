from psycopg import AsyncClientCursor, AsyncCursor, sql
from psycopg.pq import Format

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapperAsync
from django.db.backends.postgresql.base import (
    TIMESTAMPTZ_OID,
    PostgreSQLBaseDatabaseWrapper,
)
from django.db.backends.postgresql.psycopg_any import is_psycopg3, register_tzloader
from django.db.backends.utils import (
    CursorDebugWrapperAsync as BaseCursorDebugWrapperAsync,
)
from django.utils.functional import cached_property

if not is_psycopg3:
    raise ImproperlyConfigured(
        "psycopg3 is not installed. Please install psycopg3 to use the async backend."
    )


class DatabaseWrapper(PostgreSQLBaseDatabaseWrapper, BaseDatabaseWrapperAsync):
    def get_connection_params(self):
        conn_params = self._base_get_connection_params()
        server_side_binding = conn_params.pop("server_side_binding", None)
        conn_params.setdefault(
            "cursor_factory",
            AsyncServerBindingCursor
            if is_psycopg3 and server_side_binding is True
            else AsyncCursor,
        )
        return conn_params

    async def get_database_version(self):
        """
        Return a tuple of the database's version.
        E.g. for pg_version 120004, return (12, 4).
        """
        return divmod(await self.pg_version, 10000)

    async def get_new_connection(self, conn_params):
        (set_isolation_level,) = self._prepare_get_new_connection()
        connection = await self.Database.AsyncConnection.connect(**conn_params)
        if set_isolation_level:
            connection.isolation_level = self.isolation_level
        return connection

    async def ensure_timezone(self):
        if self.connection is None:
            return False
        conn_timezone_name = self.connection.info.parameter_status("TimeZone")
        timezone_name = self.timezone_name
        if timezone_name and conn_timezone_name != timezone_name:
            async with self.connection.cursor() as cursor:
                await cursor.execute(self.ops.set_time_zone_sql(), [timezone_name])
            return True
        return False

    async def ensure_role(self):
        if self.connection is None:
            return False
        if new_role := self.settings_dict.get("OPTIONS", {}).get("assume_role"):
            async with self.connection.cursor() as cursor:
                sql = self.ops.compose_sql("SET ROLE %s", [new_role])
                await cursor.execute(sql)
            return True
        return False

    async def init_connection_state(self):
        await super().init_connection_state()

        # Commit after setting the time zone.
        commit_tz = await self.ensure_timezone()
        # Set the role on the connection. This is useful if the credential used
        # to login is not the same as the role that owns database resources. As
        # can be the case when using temporary or ephemeral credentials.
        commit_role = await self.ensure_role()

        if (commit_role or commit_tz) and not await self.get_autocommit():
            await self.connection.commit()

    async def create_cursor(self, name=None):
        if name:
            # In autocommit mode, the cursor will be used outside of a
            # transaction, hence use a holdable cursor.
            cursor = self.connection.cursor(
                name, scrollable=False, withhold=self.connection.autocommit
            )
        else:
            cursor = self.connection.cursor()

        # Register the cursor timezone only if the connection disagrees, to
        # avoid copying the adapter map.
        tzloader = self.connection.adapters.get_loader(TIMESTAMPTZ_OID, Format.TEXT)
        if self.timezone != tzloader.timezone:
            register_tzloader(self.timezone, cursor)
        return cursor

    async def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
            await self.connection.set_autocommit(autocommit)

    @cached_property
    async def pg_version(self):
        async with self.temporary_connection():
            return self.connection.info.server_version

    def make_debug_cursor(self, cursor):
        return CursorDebugWrapper(cursor, self)


class CursorMixin:
    """
    A subclass of psycopg cursor implementing callproc.
    """

    async def callproc(self, name, args=None):
        if not isinstance(name, sql.Identifier):
            name = sql.Identifier(name)

        qparts = [sql.SQL("SELECT * FROM "), name, sql.SQL("(")]
        if args:
            for item in args:
                qparts.append(sql.Literal(item))
                qparts.append(sql.SQL(","))
            del qparts[-1]

        qparts.append(sql.SQL(")"))
        stmt = sql.Composed(qparts)
        await self.execute(stmt)
        return args


class AsyncServerBindingCursor(CursorMixin, AsyncCursor):
    pass


class AsyncCursor(CursorMixin, AsyncClientCursor):
    pass


class CursorDebugWrapper(BaseCursorDebugWrapperAsync):
    def copy(self, statement):
        with self.debug_sql(statement):
            return self.cursor.copy(statement)
