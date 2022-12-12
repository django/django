from enum import IntEnum

from psycopg2 import errors, extensions, sql  # NOQA
from psycopg2.extras import DateRange, DateTimeRange, DateTimeTZRange, Inet  # NOQA
from psycopg2.extras import Json as Jsonb  # NOQA
from psycopg2.extras import NumericRange, Range  # NOQA

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
