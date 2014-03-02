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
COMPLEX_OVERRIDE_SETTINGS = set(['DATABASES'])


@receiver(setting_changed)
def clear_cache_handlers(**kwargs):
    if kwargs['setting'] == 'CACHES':
        from django.core.cache import caches
        caches._caches = threading.local()


@receiver(setting_changed)
def update_installed_apps(**kwargs):
    if kwargs['setting'] == 'INSTALLED_APPS':
        # Rebuild any AppDirectoriesFinder instance.
        from django.contrib.staticfiles.finders import get_finder
        get_finder.cache_clear()
        # Rebuild management commands cache
        from django.core.management import get_commands
        get_commands.cache_clear()
        # Rebuild templatetags module cache.
        from django.template import base as mod
        mod.templatetags_modules = []
        # Rebuild app_template_dirs cache.
        from django.template.loaders import app_directories as mod
        mod.app_template_dirs = mod.calculate_app_template_dirs()
        # Rebuild translations cache.
        from django.utils.translation import trans_real
        trans_real._translations = {}


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
    if kwargs['setting'] in {'LANGUAGES', 'LANGUAGE_CODE', 'LOCALE_PATHS'}:
        from django.utils.translation import trans_real
        trans_real._default = None
        trans_real._active = threading.local()
    if kwargs['setting'] in {'LANGUAGES', 'LOCALE_PATHS'}:
        from django.utils.translation import trans_real
        trans_real._translations = {}
        trans_real.check_for_language.cache_clear()


@receiver(setting_changed)
def file_storage_changed(**kwargs):
    if kwargs['setting'] in ('MEDIA_ROOT', 'DEFAULT_FILE_STORAGE'):
        from django.core.files.storage import default_storage
        default_storage._wrapped = empty


@receiver(setting_changed)
def complex_setting_changed(**kwargs):
    if kwargs['enter'] and kwargs['setting'] in COMPLEX_OVERRIDE_SETTINGS:
        # Considering the current implementation of the signals framework,
        # stacklevel=5 shows the line containing the override_settings call.
        warnings.warn("Overriding setting %s can lead to unexpected behavior."
                      % kwargs['setting'], stacklevel=5)


@receiver(setting_changed)
def root_urlconf_changed(**kwargs):
    if kwargs['setting'] == 'ROOT_URLCONF':
        from django.core.urlresolvers import clear_url_caches
        clear_url_caches()
