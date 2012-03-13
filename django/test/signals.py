from django.conf import settings
from django.db import close_connection
from django.dispatch import Signal

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value"])

# Close the database connection to re-establish it with the proper time zone.
def close_connection_on_time_zone_change(**kwargs):
    if (kwargs['setting'] == 'USE_TZ'
        or (kwargs['setting'] == 'TIME_ZONE' and not settings.USE_TZ)):
        close_connection()
setting_changed.connect(close_connection_on_time_zone_change)
