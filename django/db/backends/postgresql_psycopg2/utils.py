from django.utils.timezone import utc


def utc_tzinfo_factory(offset):
    if offset != 0:
        raise AssertionError("database connection isn't set to UTC")
    return utc
