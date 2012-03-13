from django.conf import settings
from django.db import connections
from django.dispatch import Signal

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value"])

def update_connections_time_zone(**kwargs):
    if kwargs['setting'] == 'USE_TZ' and settings.TIME_ZONE != 'UTC':
        USE_TZ, TIME_ZONE = kwargs['value'], settings.TIME_ZONE
    elif kwargs['setting'] == 'TIME_ZONE' and not settings.USE_TZ:
        USE_TZ, TIME_ZONE = settings.USE_TZ, kwargs['value']
    else:   # no need to change the database connnections' time zones
        return

    tz = 'UTC' if USE_TZ else TIME_ZONE
    for conn in connections.all():
        tz_sql = conn.ops.set_time_zone_sql()
        if tz_sql:
            conn.cursor().execute(tz_sql, [tz])

setting_changed.connect(update_connections_time_zone)
