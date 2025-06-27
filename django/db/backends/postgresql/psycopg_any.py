import ipaddress
from functools import lru_cache

try:
    from psycopg import ClientCursor, IsolationLevel, adapt, adapters, errors, sql
    from psycopg.postgres import types
    from psycopg.types.datetime import TimestamptzLoader
    from psycopg.types.json import Jsonb
    from psycopg.types.range import Range, RangeDumper
    from psycopg.types.string import TextLoader

    Inet = ipaddress.ip_address

    DateRange = DateTimeRange = DateTimeTZRange = NumericRange = Range
    RANGE_TYPES = (Range,)

    TSRANGE_OID = types["tsrange"].oid
    TSTZRANGE_OID = types["tstzrange"].oid

    def mogrify(sql, params, connection):
        with connection.cursor() as cursor:
            return ClientCursor(cursor.connection).mogrify(sql, params)

    # Adapters.
    class BaseTzLoader(TimestamptzLoader):
        """
        Load a PostgreSQL timestamptz using the a specific timezone.
        The timezone can be None too, in which case it will be chopped.
        """

        timezone = None

        def load(self, data):
            res = super().load(data)
            return res.replace(tzinfo=self.timezone)

    def register_tzloader(tz, context):
        class SpecificTzLoader(BaseTzLoader):
            timezone = tz

        context.adapters.register_loader("timestamptz", SpecificTzLoader)

    class DjangoRangeDumper(RangeDumper):
        """A Range dumper customized for Django."""

        def upgrade(self, obj, format):
            # Dump ranges containing naive datetimes as tstzrange, because
            # Django doesn't use tz-aware ones.
            dumper = super().upgrade(obj, format)
            if dumper is not self and dumper.oid == TSRANGE_OID:
                dumper.oid = TSTZRANGE_OID
            return dumper

    @lru_cache
    def get_adapters_template(use_tz, timezone):
        # Create an adapters map extending the base one.
        ctx = adapt.AdaptersMap(adapters)
        # Register a no-op dumper to avoid a round trip from psycopg version 3
        # decode to json.dumps() to json.loads(), when using a custom decoder
        # in JSONField.
        ctx.register_loader("jsonb", TextLoader)
        # Don't convert automatically from PostgreSQL network types to Python
        # ipaddress.
        ctx.register_loader("inet", TextLoader)
        ctx.register_loader("cidr", TextLoader)
        ctx.register_dumper(Range, DjangoRangeDumper)
        # Register a timestamptz loader configured on self.timezone.
        # This, however, can be overridden by create_cursor.
        register_tzloader(timezone, ctx)
        return ctx

    is_psycopg3 = True

except ImportError:
    from enum import IntEnum

    from psycopg2 import errors, extensions, sql  # NOQA
    from psycopg2.extras import (  # NOQA
        DateRange,
        DateTimeRange,
        DateTimeTZRange,
        Inet,
        Json,
        NumericRange,
        Range,
    )

    RANGE_TYPES = (DateRange, DateTimeRange, DateTimeTZRange, NumericRange)

    class IsolationLevel(IntEnum):
        READ_UNCOMMITTED = extensions.ISOLATION_LEVEL_READ_UNCOMMITTED
        READ_COMMITTED = extensions.ISOLATION_LEVEL_READ_COMMITTED
        REPEATABLE_READ = extensions.ISOLATION_LEVEL_REPEATABLE_READ
        SERIALIZABLE = extensions.ISOLATION_LEVEL_SERIALIZABLE

    def _quote(value, connection=None):
        adapted = extensions.adapt(value)
        if hasattr(adapted, "encoding"):
            adapted.encoding = "utf8"
        # getquoted() returns a quoted bytestring of the adapted value.
        return adapted.getquoted().decode()

    sql.quote = _quote

    def mogrify(sql, params, connection):
        with connection.cursor() as cursor:
            return cursor.mogrify(sql, params).decode()

    is_psycopg3 = False

    class Jsonb(Json):
        def getquoted(self):
            quoted = super().getquoted()
            return quoted + b"::jsonb"
