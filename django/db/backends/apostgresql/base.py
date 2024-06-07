"""
PostgreSQL database backend for Django.

Requires psycopg2 >= 2.8.4 or psycopg >= 3.1.8
"""

import asyncio
import threading
import time
import warnings
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError as WrappedDatabaseError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.backends.base.base import NO_DB_ALIAS, AsyncBaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.db.backends.utils import AsyncCursorDebugWrapper as AsyncBaseCursorDebugWrapper
from django.db.backends.postgresql.base import DatabaseWrapper as PGDatabaseWrapper
from django.db.utils import NotSupportedError
from django.utils.functional import cached_property
from django.utils.safestring import SafeString
from django.utils.version import get_version_tuple

try:
    import psycopg as Database
except ImportError:
    raise ImproperlyConfigured("Error loading psycopg module")


def psycopg_version():
    version = Database.__version__.split(" ", 1)[0]
    return get_version_tuple(version)


if (3,) <= psycopg_version() < (3, 1, 8):
    raise ImproperlyConfigured(
        f"psycopg version 3.1.8 or newer is required; you have {Database.__version__}"
    )


from .psycopg_any import IsolationLevel, is_psycopg3  # NOQA isort:skip

from psycopg import adapters, sql
from psycopg.pq import Format

from .psycopg_any import get_adapters_template, register_tzloader

TIMESTAMPTZ_OID = adapters.types["timestamptz"].oid


# Some of these import psycopg, so import them after checking if it's installed.
from .client import DatabaseClient  # NOQA isort:skip
from .creation import DatabaseCreation  # NOQA isort:skip
from .features import DatabaseFeatures  # NOQA isort:skip
from .introspection import DatabaseIntrospection  # NOQA isort:skip
from .operations import DatabaseOperations  # NOQA isort:skip
from .schema import DatabaseSchemaEditor  # NOQA isort:skip


def _get_varchar_column(data):
    if data["max_length"] is None:
        return "varchar"
    return "varchar(%(max_length)s)" % data


async def aensure_timezone(connection, ops, timezone_name):
    conn_timezone_name = connection.info.parameter_status("TimeZone")
    if timezone_name and conn_timezone_name != timezone_name:
        async with connection.cursor() as cursor:
            await cursor.execute(ops.set_time_zone_sql(), [timezone_name])
        return True
    return False


def ensure_role(connection, ops, role_name):
    if role_name:
        with connection.cursor() as cursor:
            sql = ops.compose_sql("SET ROLE %s", [role_name])
            cursor.execute(sql)
        return True
    return False


class DatabaseWrapper(AsyncBaseDatabaseWrapper, PGDatabaseWrapper):
    vendor = "postgresql (async)"
    display_name = "PostgreSQL (async)"

    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    @property
    def apool(self):
        pool_options = self.settings_dict["OPTIONS"].get("pool")
        if self.alias == NO_DB_ALIAS or not pool_options:
            return None

        if self.alias not in self._aconnection_pools:
            if self.settings_dict.get("CONN_MAX_AGE", 0) != 0:
                raise ImproperlyConfigured(
                    "Pooling doesn't support persistent connections."
                )
            # Set the default options.
            if pool_options is True:
                pool_options = {}

            try:
                from psycopg_pool import AsyncConnectionPool
            except ImportError as err:
                raise ImproperlyConfigured(
                    "Error loading psycopg_pool module.\nDid you install psycopg[pool]?"
                ) from err

            connect_kwargs = self.get_aconnection_params()
            # Ensure we run in autocommit, Django properly sets it later on.
            connect_kwargs["autocommit"] = True
            enable_checks = self.settings_dict["CONN_HEALTH_CHECKS"]
            pool = AsyncConnectionPool(
                kwargs=connect_kwargs,
                open=False,  # Do not open the pool during startup.
                configure=self._aconfigure_connection,
                check=AsyncConnectionPool.check_connection if enable_checks else None,
                **pool_options,
            )
            # setdefault() ensures that multiple threads don't set this in
            # parallel. Since we do not open the pool during it's init above,
            # this means that at worst during startup multiple threads generate
            # pool objects and the first to set it wins.
            self._aconnection_pools.setdefault(self.alias, pool)

        return self._aconnection_pools[self.alias]

    async def aclose_pool(self):
        if self.apool:
            await self.apool.close()
            del self._aconnection_pools[self.alias]

    async def _aclose(self):
        if self.aconnection is not None:
            # `wrap_database_errors` only works for `putconn` as long as there
            # is no `reset` function set in the pool because it is deferred
            # into a thread and not directly executed.
            with self.wrap_database_errors:
                if self.apool:
                    # Ensure the correct pool is returned. This is a workaround
                    # for tests so a pool can be changed on setting changes
                    # (e.g. USE_TZ, TIME_ZONE).
                    self.aconnection._pool.putconn(self.aconnection)
                    # Connection can no longer be used.
                    self.aconnection = None
                else:
                    return await self.aconnection.close()

    async def _close_if_health_check_failed(self):
        """Close existing connection if it fails a health check."""
        if (
            self.aconnection is None
            or not self.health_check_enabled
            or self.health_check_done
        ):
            return

        if not await self.ais_usable():
            await self.aclose()
        self.health_check_done = True

    async def _aconfigure_connection(self, connection):
        # This function is called from init_connection_state and from the
        # psycopg pool itself after a connection is opened. Make sure that
        # whatever is done here does not access anything on self aside from
        # variables.

        # Commit after setting the time zone.
        commit_tz = await aensure_timezone(connection, self.ops, self.timezone_name)
        # Set the role on the connection. This is useful if the credential used
        # to login is not the same as the role that owns database resources. As
        # can be the case when using temporary or ephemeral credentials.
        role_name = self.settings_dict["OPTIONS"].get("assume_role")
        commit_role = ensure_role(connection, self.ops, role_name)

        return commit_role or commit_tz

    async def aget_database_version(self):
        """
        Return a tuple of the database's version.
        E.g. for pg_version 120004, return (12, 4).
        """
        pg_version = await self.apg_version
        return divmod(pg_version, 10000)

    async def acheck_database_version_supported(self):
        """
        Raise an error if the database version isn't supported by this
        version of Django.
        """
        str_db_version = await self.aget_database_version()
        if (
            self.features.minimum_database_version is not None
            and str_db_version < self.features.minimum_database_version
        ):
            db_version = ".".join(map(str, str_db_version))
            min_db_version = ".".join(map(str, self.features.minimum_database_version))
            raise NotSupportedError(
                f"{self.display_name} {min_db_version} or later is required "
                f"(found {db_version})."
            )

    async def aensure_timezone(self):
        # Close the pool so new connections pick up the correct timezone.
        await self.aclose_pool()
        if self.aconnection is None:
            return False
        return await aensure_timezone(self.aconnection, self.ops, self.timezone_name)

    def get_aconnection_params(self):
        settings_dict = self.settings_dict
        # None may be used to connect to the default 'postgres' db
        if settings_dict["NAME"] == "" and not settings_dict["OPTIONS"].get("service"):
            raise ImproperlyConfigured(
                "settings.ASYNC_DATABASES is improperly configured. "
                "Please supply the NAME or OPTIONS['service'] value."
            )
        if len(settings_dict["NAME"] or "") > self.ops.max_name_length():
            raise ImproperlyConfigured(
                "The database name '%s' (%d characters) is longer than "
                "PostgreSQL's limit of %d characters. Supply a shorter NAME "
                "in settings.ASYNC_DATABASES."
                % (
                    settings_dict["NAME"],
                    len(settings_dict["NAME"]),
                    self.ops.max_name_length(),
                )
            )
        if settings_dict["NAME"]:
            conn_params = {
                "dbname": settings_dict["NAME"],
                **settings_dict["OPTIONS"],
            }
        elif settings_dict["NAME"] is None:
            # Connect to the default 'postgres' db.
            settings_dict["OPTIONS"].pop("service", None)
            conn_params = {"dbname": "postgres", **settings_dict["OPTIONS"]}
        else:
            conn_params = {**settings_dict["OPTIONS"]}
        conn_params["client_encoding"] = "UTF8"

        conn_params.pop("assume_role", None)
        conn_params.pop("isolation_level", None)

        pool_options = conn_params.pop("pool", None)
        if pool_options and not is_psycopg3:
            raise ImproperlyConfigured("Database pooling requires psycopg >= 3")

        server_side_binding = conn_params.pop("server_side_binding", None)
        conn_params.setdefault(
            "cursor_factory",
            (
                AsyncServerBindingCursor
                if is_psycopg3 and server_side_binding is True
                else AsyncCursor
            ),
        )
        if settings_dict["USER"]:
            conn_params["user"] = settings_dict["USER"]
        if settings_dict["PASSWORD"]:
            conn_params["password"] = settings_dict["PASSWORD"]
        if settings_dict["HOST"]:
            conn_params["host"] = settings_dict["HOST"]
        if settings_dict["PORT"]:
            conn_params["port"] = settings_dict["PORT"]
        if is_psycopg3:
            conn_params["context"] = get_adapters_template(
                settings.USE_TZ, self.timezone
            )
            # Disable prepared statements by default to keep connection poolers
            # working. Can be reenabled via OPTIONS in the settings dict.
            conn_params["prepare_threshold"] = conn_params.pop(
                "prepare_threshold", None
            )
        return conn_params

    async def aget_new_connection(self, conn_params):
        # self.isolation_level must be set:
        # - after connecting to the database in order to obtain the database's
        #   default when no value is explicitly specified in options.
        # - before calling _set_autocommit() because if autocommit is on, that
        #   will set connection.isolation_level to ISOLATION_LEVEL_AUTOCOMMIT.
        options = self.settings_dict["OPTIONS"]
        set_isolation_level = False
        try:
            isolation_level_value = options["isolation_level"]
        except KeyError:
            self.isolation_level = IsolationLevel.READ_COMMITTED
        else:
            # Set the isolation level to the value from OPTIONS.
            try:
                self.isolation_level = IsolationLevel(isolation_level_value)
                set_isolation_level = True
            except ValueError:
                raise ImproperlyConfigured(
                    f"Invalid transaction isolation level {isolation_level_value} "
                    f"specified. Use one of the psycopg.IsolationLevel values."
                )
        if self.pool:
            # If nothing else has opened the pool, open it now.
            self.pool.open()
            connection = self.pool.getconn()
        else:
            connection = await self.Database.AsyncConnection.connect(**conn_params)
        if set_isolation_level:
            connection.isolation_level = self.isolation_level
        return connection

    async def _aclose(self):
        if self.aconnection is not None:
            # `wrap_database_errors` only works for `putconn` as long as there
            # is no `reset` function set in the pool because it is deferred
            # into a thread and not directly executed.
            with self.wrap_database_errors:
                if self.apool:
                    # Ensure the correct pool is returned. This is a workaround
                    # for tests so a pool can be changed on setting changes
                    # (e.g. USE_TZ, TIME_ZONE).
                    await self.aconnection._pool.putconn(self.aconnection)
                    # Connection can no longer be used.
                    self.aconnection = None
                else:
                    return await self.aconnection.close()

    async def ainit_connection_state(self):
        await super().ainit_connection_state()

        if self.aconnection is not None and not self.apool:
            commit = await self._aconfigure_connection(self.aconnection)

            if commit and not self.get_autocommit():
                await self.aconnection.commit()

    async def aconnect(self):
        """Connect to the database. Assume that the connection is closed."""
        # Check for invalid configurations.
        self.check_settings()
        # In case the previous connection was closed while in an atomic block
        self.in_atomic_block = False
        self.savepoint_ids = []
        self.atomic_blocks = []
        self.needs_rollback = False
        # Reset parameters defining when to close/health-check the connection.
        self.health_check_enabled = self.settings_dict["CONN_HEALTH_CHECKS"]
        max_age = self.settings_dict["CONN_MAX_AGE"]
        self.close_at = None if max_age is None else time.monotonic() + max_age
        self.closed_in_transaction = False
        self.errors_occurred = False
        # New connections are healthy.
        self.health_check_done = True
        # Establish the connection
        conn_params = self.get_aconnection_params()
        self.aconnection = await self.aget_new_connection(conn_params)
        await self.aset_autocommit(self.settings_dict["AUTOCOMMIT"])
        await self.ainit_connection_state()
        connection_created.send(sender=self.__class__, connection=self)

        self.run_on_commit = []

    def create_async_cursor(self, name=None):
        if name:
            if (
                self.settings_dict["OPTIONS"].get("server_side_binding") is not True
            ):
                # psycopg >= 3 forces the usage of server-side bindings for
                # named cursors so a specialized class that implements
                # server-side cursors while performing client-side bindings
                # must be used if `server_side_binding` is disabled (default).
                cursor = AsyncServerSideCursor(
                    self.aconnection,
                    name=name,
                    scrollable=False,
                    withhold=self.aconnection.autocommit,
                )
            else:
                # In autocommit mode, the cursor will be used outside of a
                # transaction, hence use a holdable cursor.
                cursor = self.aconnection.cursor(
                    name, scrollable=False, withhold=self.aconnection.autocommit
                )
        else:
            cursor = self.aconnection.cursor()

        # Register the cursor timezone only if the connection disagrees, to
        # avoid copying the adapter map.
        tzloader = self.aconnection.adapters.get_loader(TIMESTAMPTZ_OID, Format.TEXT)
        if self.timezone != tzloader.timezone:
            register_tzloader(self.timezone, cursor)
        return cursor

    async def _aset_autocommit(self, autocommit):
        with self.wrap_database_errors:
            await self.aconnection.set_autocommit(autocommit)

    async def acheck_constraints(self, table_names=None):
        """
        Check constraints by setting them to immediate. Return them to deferred
        afterward.
        """
        async with self.acursor() as cursor:
            await cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            await cursor.execute("SET CONSTRAINTS ALL DEFERRED")

    async def ais_usable(self):
        if self.aconnection is None:
            return False
        try:
            # Use a psycopg cursor directly, bypassing Django's utilities.
            async with self.aconnection.cursor() as cursor:
                await cursor.execute("SELECT 1")
        except Database.Error:
            return False
        else:
            return True

    @contextmanager
    async def _anodb_cursor(self):
        cursor = None
        try:
            async with super()._anodb_cursor() as cursor:
                yield cursor
        except (Database.DatabaseError, WrappedDatabaseError):
            if cursor is not None:
                raise
            warnings.warn(
                "Normally Django will use a connection to the 'postgres' database "
                "to avoid running initialization queries against the production "
                "database when it's not needed (for example, when running tests). "
                "Django was unable to create a connection to the 'postgres' database "
                "and will use the first PostgreSQL database instead.",
                RuntimeWarning,
            )
            for connection in connections.all():
                if (
                    connection.vendor == "postgresql"
                    and connection.settings_dict["NAME"] != "postgres"
                ):
                    conn = self.__class__(
                        {
                            **self.settings_dict,
                            "NAME": connection.settings_dict["NAME"],
                        },
                        alias=self.alias,
                    )
                    try:
                        async with conn.acursor() as cursor:
                            yield cursor
                    finally:
                        await conn.aclose()
                    break
            else:
                raise

    @cached_property
    async def apg_version(self):
        # unused
        async with self.atemporary_connection():
            return self.aconnection.info.server_version


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


class AsyncServerBindingCursor(CursorMixin, Database.AsyncClientCursor):
    pass


class AsyncCursor(CursorMixin, Database.AsyncClientCursor):
    pass


class AsyncServerSideCursor(
    CursorMixin, Database.client_cursor.ClientCursorMixin, Database.AsyncServerCursor
):
    """
    psycopg >= 3 forces the usage of server-side bindings when using named
    cursors but the ORM doesn't yet support the systematic generation of
    prepareable SQL (#20516).

    ClientCursorMixin forces the usage of client-side bindings while
    ServerCursor implements the logic required to declare and scroll
    through named cursors.

    Mixing ClientCursorMixin in wouldn't be necessary if Cursor allowed to
    specify how parameters should be bound instead, which ServerCursor
    would inherit, but that's not the case.
    """


class AsyncCursorDebugWrapper(AsyncBaseCursorDebugWrapper):
    def copy(self, statement):
        with self.debug_sql(statement):
            return self.cursor.copy(statement)
