import os
import time
import threading
import warnings

from django.conf import settings
from django.db import connections
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.utils.functional import empty

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value", "enter"])

# Most setting_changed receivers are supposed to be added below,
# except for cases where the receiver is related to a contrib app.

# Settings that may not work well when using 'override_settings' (#19031)
COMPLEX_OVERRIDE_SETTINGS = {'DATABASES'}


@receiver(setting_changed)
def clear_cache_handlers(**kwargs):
    if kwargs['setting'] == 'CACHES':
        from django.core.cache import caches
        caches._caches = threading.local()


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
def clear_loaddata_cache(**kwargs):
    if kwargs['setting'] in {'FIXTURE_DIRS', 'INSTALLED_APPS', 'SERIALIZATION_MODULES'}:
        from django.core.management.commands import loaddata
        loaddata.Command.find_fixtures.cache_clear()


@receiver(setting_changed)
def clear_media_storage(**kwargs):
    if kwargs['setting'] in {'MEDIA_ROOT', 'DEFAULT_FILE_STORAGE'}:
        from django.core.files.storage import default_storage
        default_storage._wrapped = empty


@receiver(setting_changed)
def clear_serializers_cache(**kwargs):
    if kwargs['setting'] == 'SERIALIZATION_MODULES':
        from django.core import serializers
        serializers._serializers = {}


@receiver(setting_changed)
def clear_static_finders_cache(**kwargs):
    if kwargs['setting'] in {'INSTALLED_DIRS', 'STATICFILES_DIRS'}:
        from django.contrib.staticfiles.finders import get_finder
        get_finder.cache_clear()


@receiver(setting_changed)
def clear_template_context_processors_cache(**kwargs):
    if kwargs['setting'] == 'TEMPLATE_CONTEXT_PROCESSORS':
        from django.template import context
        context._standard_context_processors = None


@receiver(setting_changed)
def clear_template_loaders_cache(**kwargs):
    if kwargs['setting'] in {'INSTALLED_APPS', 'TEMPLATE_LOADERS'}:
        from django.template import loader
        loader.template_source_loaders = None
        from django.template.loaders import app_directories
        app_directories.app_template_dirs = []


@receiver(setting_changed)
def clear_templatetags_cache(**kwargs):
    if kwargs['setting'] == 'INSTALLED_APPS':
        from django.template import base
        base.templatetags_modules = []


@receiver(setting_changed)
def clear_i18n_caches(**kwargs):
    if kwargs['setting'] in {'INSTALLED_APPS', 'LANGUAGE_CODE', 'LOCALE_PATHS'}:
        from django.utils.translation import trans_real
        trans_real._translations = {}
        trans_real._active = threading.local()
        trans_real._default = None
        trans_real.check_for_language.cache_clear()


@receiver(setting_changed)
def complex_setting_changed(**kwargs):
    if kwargs['enter'] and kwargs['setting'] in COMPLEX_OVERRIDE_SETTINGS:
        # Considering the current implementation of the signals framework,
        # stacklevel=5 shows the line containing the override_settings call.
        warnings.warn("Overriding setting %s can lead to unexpected behaviour."
                      % kwargs['setting'], stacklevel=5)
