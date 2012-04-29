import os
import time

from django.conf import settings
from django.db import connections
from django.dispatch import receiver, Signal
from django.template import context
from django.utils import timezone

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value"])


@receiver(setting_changed)
def update_connections_time_zone(**kwargs):
    if kwargs['setting'] == 'TIME_ZONE':
        # Reset process time zone
        if hasattr(time, 'tzset'):
            if kwargs['value']:
                os.environ['TZ'] = kwargs['value']
            else:
                os.environ.pop('TZ', None)
            time.tzset()

        # Reset local time zone cache
        timezone._localtime = None

    # Reset the database connections' time zone
    if kwargs['setting'] == 'USE_TZ' and settings.TIME_ZONE != 'UTC':
        USE_TZ, TIME_ZONE = kwargs['value'], settings.TIME_ZONE
    elif kwargs['setting'] == 'TIME_ZONE' and not settings.USE_TZ:
        USE_TZ, TIME_ZONE = settings.USE_TZ, kwargs['value']
    else:
        # no need to change the database connnections' time zones
        return
    tz = 'UTC' if USE_TZ else TIME_ZONE
    for conn in connections.all():
        conn.settings_dict['TIME_ZONE'] = tz
        tz_sql = conn.ops.set_time_zone_sql()
        if tz_sql:
            conn.cursor().execute(tz_sql, [tz])


@receiver(setting_changed)
def clear_context_processors_cache(**kwargs):
    if kwargs['setting'] == 'TEMPLATE_CONTEXT_PROCESSORS':
        context._standard_context_processors = None
