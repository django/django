"""
Implementations of SQL functions for SQLite.
"""
import functools
import random
import statistics
import zoneinfo
from datetime import timedelta
from hashlib import md5, sha1, sha224, sha256, sha384, sha512
from math import (
    acos,
    asin,
    atan,
    atan2,
    ceil,
    cos,
    degrees,
    exp,
    floor,
    fmod,
    log,
    pi,
    radians,
    sin,
    sqrt,
    tan,
)
from re import search as re_search

from django.db.backends.utils import (
    split_tzname_delta,
    typecast_time,
    typecast_timestamp,
)
from django.utils import timezone
from django.utils.duration import duration_microseconds


def register(connection):
    create_deterministic_function = functools.partial(
        connection.create_function,
        deterministic=True,
    )
    create_deterministic_function("django_date_extract", 2, _sqlite_datetime_extract)
    create_deterministic_function("django_date_trunc", 4, _sqlite_date_trunc)
    create_deterministic_function(
        "django_datetime_cast_date", 3, _sqlite_datetime_cast_date
    )
    create_deterministic_function(
        "django_datetime_cast_time", 3, _sqlite_datetime_cast_time
    )
    create_deterministic_function(
        "django_datetime_extract", 4, _sqlite_datetime_extract
    )
    create_deterministic_function("django_datetime_trunc", 4, _sqlite_datetime_trunc)
    create_deterministic_function("django_time_extract", 2, _sqlite_time_extract)
    create_deterministic_function("django_time_trunc", 4, _sqlite_time_trunc)
    create_deterministic_function("django_time_diff", 2, _sqlite_time_diff)
    create_deterministic_function("django_timestamp_diff", 2, _sqlite_timestamp_diff)
    create_deterministic_function("django_format_dtdelta", 3, _sqlite_format_dtdelta)
    create_deterministic_function("regexp", 2, _sqlite_regexp)
    create_deterministic_function("BITXOR", 2, _sqlite_bitxor)
    create_deterministic_function("COT", 1, _sqlite_cot)
    create_deterministic_function("LPAD", 3, _sqlite_lpad)
    create_deterministic_function("MD5", 1, _sqlite_md5)
    create_deterministic_function("REPEAT", 2, _sqlite_repeat)
    create_deterministic_function("REVERSE", 1, _sqlite_reverse)
    create_deterministic_function("RPAD", 3, _sqlite_rpad)
    create_deterministic_function("SHA1", 1, _sqlite_sha1)
    create_deterministic_function("SHA224", 1, _sqlite_sha224)
    create_deterministic_function("SHA256", 1, _sqlite_sha256)
    create_deterministic_function("SHA384", 1, _sqlite_sha384)
    create_deterministic_function("SHA512", 1, _sqlite_sha512)
    create_deterministic_function("SIGN", 1, _sqlite_sign)
    # Don't use the built-in RANDOM() function because it returns a value
    # in the range [-1 * 2^63, 2^63 - 1] instead of [0, 1).
    connection.create_function("RAND", 0, random.random)
    connection.create_aggregate("STDDEV_POP", 1, StdDevPop)
    connection.create_aggregate("STDDEV_SAMP", 1, StdDevSamp)
    connection.create_aggregate("VAR_POP", 1, VarPop)
    connection.create_aggregate("VAR_SAMP", 1, VarSamp)
    # Some math functions are enabled by default in SQLite 3.35+.
    sql = "select sqlite_compileoption_used('ENABLE_MATH_FUNCTIONS')"
    if not connection.execute(sql).fetchone()[0]:
        create_deterministic_function("ACOS", 1, _sqlite_acos)
        create_deterministic_function("ASIN", 1, _sqlite_asin)
        create_deterministic_function("ATAN", 1, _sqlite_atan)
        create_deterministic_function("ATAN2", 2, _sqlite_atan2)
        create_deterministic_function("CEILING", 1, _sqlite_ceiling)
        create_deterministic_function("COS", 1, _sqlite_cos)
        create_deterministic_function("DEGREES", 1, _sqlite_degrees)
        create_deterministic_function("EXP", 1, _sqlite_exp)
        create_deterministic_function("FLOOR", 1, _sqlite_floor)
        create_deterministic_function("LN", 1, _sqlite_ln)
        create_deterministic_function("LOG", 2, _sqlite_log)
        create_deterministic_function("MOD", 2, _sqlite_mod)
        create_deterministic_function("PI", 0, _sqlite_pi)
        create_deterministic_function("POWER", 2, _sqlite_power)
        create_deterministic_function("RADIANS", 1, _sqlite_radians)
        create_deterministic_function("SIN", 1, _sqlite_sin)
        create_deterministic_function("SQRT", 1, _sqlite_sqrt)
        create_deterministic_function("TAN", 1, _sqlite_tan)


def _sqlite_datetime_parse(dt, tzname=None, conn_tzname=None):
    if dt is None:
        return None
    try:
        dt = typecast_timestamp(dt)
    except (TypeError, ValueError):
        return None
    if conn_tzname:
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(conn_tzname))
    if tzname is not None and tzname != conn_tzname:
        tzname, sign, offset = split_tzname_delta(tzname)
        if offset:
            hours, minutes = offset.split(":")
            offset_delta = timedelta(hours=int(hours), minutes=int(minutes))
            dt += offset_delta if sign == "+" else -offset_delta
        dt = timezone.localtime(dt, zoneinfo.ZoneInfo(tzname))
    return dt


def _sqlite_date_trunc(lookup_type, dt, tzname, conn_tzname):
    dt = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt is None:
        return None
    if lookup_type == "year":
        return f"{dt.year:04d}-01-01"
    elif lookup_type == "quarter":
        month_in_quarter = dt.month - (dt.month - 1) % 3
        return f"{dt.year:04d}-{month_in_quarter:02d}-01"
    elif lookup_type == "month":
        return f"{dt.year:04d}-{dt.month:02d}-01"
    elif lookup_type == "week":
        dt -= timedelta(days=dt.weekday())
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
    elif lookup_type == "day":
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
    raise ValueError(f"Unsupported lookup type: {lookup_type!r}")


def _sqlite_time_trunc(lookup_type, dt, tzname, conn_tzname):
    if dt is None:
        return None
    dt_parsed = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt_parsed is None:
        try:
            dt = typecast_time(dt)
        except (ValueError, TypeError):
            return None
    else:
        dt = dt_parsed
    if lookup_type == "hour":
        return f"{dt.hour:02d}:00:00"
    elif lookup_type == "minute":
        return f"{dt.hour:02d}:{dt.minute:02d}:00"
    elif lookup_type == "second":
        return f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
    raise ValueError(f"Unsupported lookup type: {lookup_type!r}")


def _sqlite_datetime_cast_date(dt, tzname, conn_tzname):
    dt = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt is None:
        return None
    return dt.date().isoformat()


def _sqlite_datetime_cast_time(dt, tzname, conn_tzname):
    dt = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt is None:
        return None
    return dt.time().isoformat()


def _sqlite_datetime_extract(lookup_type, dt, tzname=None, conn_tzname=None):
    dt = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt is None:
        return None
    if lookup_type == "week_day":
        return (dt.isoweekday() % 7) + 1
    elif lookup_type == "iso_week_day":
        return dt.isoweekday()
    elif lookup_type == "week":
        return dt.isocalendar()[1]
    elif lookup_type == "quarter":
        return ceil(dt.month / 3)
    elif lookup_type == "iso_year":
        return dt.isocalendar()[0]
    else:
        return getattr(dt, lookup_type)


def _sqlite_datetime_trunc(lookup_type, dt, tzname, conn_tzname):
    dt = _sqlite_datetime_parse(dt, tzname, conn_tzname)
    if dt is None:
        return None
    if lookup_type == "year":
        return f"{dt.year:04d}-01-01 00:00:00"
    elif lookup_type == "quarter":
        month_in_quarter = dt.month - (dt.month - 1) % 3
        return f"{dt.year:04d}-{month_in_quarter:02d}-01 00:00:00"
    elif lookup_type == "month":
        return f"{dt.year:04d}-{dt.month:02d}-01 00:00:00"
    elif lookup_type == "week":
        dt -= timedelta(days=dt.weekday())
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} 00:00:00"
    elif lookup_type == "day":
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} 00:00:00"
    elif lookup_type == "hour":
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:00:00"
    elif lookup_type == "minute":
        return (
            f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} "
            f"{dt.hour:02d}:{dt.minute:02d}:00"
        )
    elif lookup_type == "second":
        return (
            f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} "
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
        )
    raise ValueError(f"Unsupported lookup type: {lookup_type!r}")


def _sqlite_time_extract(lookup_type, dt):
    if dt is None:
        return None
    try:
        dt = typecast_time(dt)
    except (ValueError, TypeError):
        return None
    return getattr(dt, lookup_type)


def _sqlite_prepare_dtdelta_param(conn, param):
    if conn in ["+", "-"]:
        if isinstance(param, int):
            return timedelta(0, 0, param)
        else:
            return typecast_timestamp(param)
    return param


def _sqlite_format_dtdelta(connector, lhs, rhs):
    """
    LHS and RHS can be either:
    - An integer number of microseconds
    - A string representing a datetime
    - A scalar value, e.g. float
    """
    if connector is None or lhs is None or rhs is None:
        return None
    connector = connector.strip()
    try:
        real_lhs = _sqlite_prepare_dtdelta_param(connector, lhs)
        real_rhs = _sqlite_prepare_dtdelta_param(connector, rhs)
    except (ValueError, TypeError):
        return None
    if connector == "+":
        # typecast_timestamp() returns a date or a datetime without timezone.
        # It will be formatted as "%Y-%m-%d" or "%Y-%m-%d %H:%M:%S[.%f]"
        out = str(real_lhs + real_rhs)
    elif connector == "-":
        out = str(real_lhs - real_rhs)
    elif connector == "*":
        out = real_lhs * real_rhs
    else:
        out = real_lhs / real_rhs
    return out


def _sqlite_time_diff(lhs, rhs):
    if lhs is None or rhs is None:
        return None
    left = typecast_time(lhs)
    right = typecast_time(rhs)
    return (
        (left.hour * 60 * 60 * 1000000)
        + (left.minute * 60 * 1000000)
        + (left.second * 1000000)
        + (left.microsecond)
        - (right.hour * 60 * 60 * 1000000)
        - (right.minute * 60 * 1000000)
        - (right.second * 1000000)
        - (right.microsecond)
    )


def _sqlite_timestamp_diff(lhs, rhs):
    if lhs is None or rhs is None:
        return None
    left = typecast_timestamp(lhs)
    right = typecast_timestamp(rhs)
    return duration_microseconds(left - right)


def _sqlite_regexp(pattern, string):
    if pattern is None or string is None:
        return None
    if not isinstance(string, str):
        string = str(string)
    return bool(re_search(pattern, string))


def _sqlite_acos(x):
    if x is None:
        return None
    return acos(x)


def _sqlite_asin(x):
    if x is None:
        return None
    return asin(x)


def _sqlite_atan(x):
    if x is None:
        return None
    return atan(x)


def _sqlite_atan2(y, x):
    if y is None or x is None:
        return None
    return atan2(y, x)


def _sqlite_bitxor(x, y):
    if x is None or y is None:
        return None
    return x ^ y


def _sqlite_ceiling(x):
    if x is None:
        return None
    return ceil(x)


def _sqlite_cos(x):
    if x is None:
        return None
    return cos(x)


def _sqlite_cot(x):
    if x is None:
        return None
    return 1 / tan(x)


def _sqlite_degrees(x):
    if x is None:
        return None
    return degrees(x)


def _sqlite_exp(x):
    if x is None:
        return None
    return exp(x)


def _sqlite_floor(x):
    if x is None:
        return None
    return floor(x)


def _sqlite_ln(x):
    if x is None:
        return None
    return log(x)


def _sqlite_log(base, x):
    if base is None or x is None:
        return None
    # Arguments reversed to match SQL standard.
    return log(x, base)


def _sqlite_lpad(text, length, fill_text):
    if text is None or length is None or fill_text is None:
        return None
    delta = length - len(text)
    if delta <= 0:
        return text[:length]
    return (fill_text * length)[:delta] + text


def _sqlite_md5(text):
    if text is None:
        return None
    return md5(text.encode()).hexdigest()


def _sqlite_mod(x, y):
    if x is None or y is None:
        return None
    return fmod(x, y)


def _sqlite_pi():
    return pi


def _sqlite_power(x, y):
    if x is None or y is None:
        return None
    return x**y


def _sqlite_radians(x):
    if x is None:
        return None
    return radians(x)


def _sqlite_repeat(text, count):
    if text is None or count is None:
        return None
    return text * count


def _sqlite_reverse(text):
    if text is None:
        return None
    return text[::-1]


def _sqlite_rpad(text, length, fill_text):
    if text is None or length is None or fill_text is None:
        return None
    return (text + fill_text * length)[:length]


def _sqlite_sha1(text):
    if text is None:
        return None
    return sha1(text.encode()).hexdigest()


def _sqlite_sha224(text):
    if text is None:
        return None
    return sha224(text.encode()).hexdigest()


def _sqlite_sha256(text):
    if text is None:
        return None
    return sha256(text.encode()).hexdigest()


def _sqlite_sha384(text):
    if text is None:
        return None
    return sha384(text.encode()).hexdigest()


def _sqlite_sha512(text):
    if text is None:
        return None
    return sha512(text.encode()).hexdigest()


def _sqlite_sign(x):
    if x is None:
        return None
    return (x > 0) - (x < 0)


def _sqlite_sin(x):
    if x is None:
        return None
    return sin(x)


def _sqlite_sqrt(x):
    if x is None:
        return None
    return sqrt(x)


def _sqlite_tan(x):
    if x is None:
        return None
    return tan(x)


class ListAggregate(list):
    step = list.append


class StdDevPop(ListAggregate):
    finalize = statistics.pstdev


class StdDevSamp(ListAggregate):
    finalize = statistics.stdev


class VarPop(ListAggregate):
    finalize = statistics.pvariance


class VarSamp(ListAggregate):
    finalize = statistics.variance
