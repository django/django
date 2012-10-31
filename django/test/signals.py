import os
import time

from django.conf import settings
from django.db import connections
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.utils.functional import empty

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value"])

# Most setting_changed receivers are supposed to be added below,
# except for cases where the receiver is related to a contrib app.


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
        from django.template import context
        context._standard_context_processors = None


@receiver(setting_changed)
def clear_template_loaders_cache(**kwargs):
    if kwargs['setting'] == 'TEMPLATE_LOADERS':
        from django.template import loader
        loader.template_source_loaders = None


@receiver(setting_changed)
def clear_serializers_cache(**kwargs):
    if kwargs['setting'] == 'SERIALIZATION_MODULES':
        from django.core import serializers
        serializers._serializers = {}


@receiver(setting_changed)
def language_changed(**kwargs):
    if kwargs['setting'] in ('LOCALE_PATHS', 'LANGUAGE_CODE'):
        from django.utils.translation import trans_real
        trans_real._default = None
        if kwargs['setting'] == 'LOCALE_PATHS':
            trans_real._translations = {}

@receiver(setting_changed)
def file_storage_changed(**kwargs):
    if kwargs['setting'] in ('MEDIA_ROOT', 'DEFAULT_FILE_STORAGE'):
        from django.core.files.storage import default_storage
        default_storage._wrapped = empty
