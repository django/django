from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def parse_datetime_with_timezone_support(value):
    dt = parse_datetime(value)
    # Confirm that dt is naive before overwriting its tzinfo.
    if dt is not None and settings.USE_TZ and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
