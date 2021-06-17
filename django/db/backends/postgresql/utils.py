from django.utils.timezone import utc


def utc_tzinfo_factory(offset):
    # Offset is an int in psycopg2 < 2.9, then switched to timedelta.
    if offset:
        raise AssertionError("database connection isn't set to UTC")
    return utc
