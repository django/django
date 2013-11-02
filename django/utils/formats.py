from __future__ import absolute_import  # Avoid importing `importlib` from this package.

import decimal
import datetime
from importlib import import_module
import unicodedata

from django.conf import settings
from django.utils import dateformat, numberformat, datetime_safe
from django.utils.encoding import force_str
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils import six
from django.utils.translation import get_language, to_locale, check_for_language

# format_cache is a mapping from (format_type, lang) to the format string.
# By using the cache, it is possible to avoid running get_format_modules
# repeatedly.
_format_cache = {}
_format_modules_cache = {}

ISO_INPUT_FORMATS = {
    'DATE_INPUT_FORMATS': ('%Y-%m-%d',),
    'TIME_INPUT_FORMATS': ('%H:%M:%S', '%H:%M:%S.%f', '%H:%M'),
    'DATETIME_INPUT_FORMATS': (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    ),
}


def reset_format_cache():
    """Clear any cached formats.

    This method is provided primarily for testing purposes,
    so that the effects of cached formats can be removed.
    """
    global _format_cache, _format_modules_cache
    _format_cache = {}
    _format_modules_cache = {}


def iter_format_modules(lang, format_module_path=None):
    """
    Does the heavy lifting of finding format modules.
    """
    if check_for_language(lang):
        format_locations = ['django.conf.locale.%s']
        if format_module_path:
            format_locations.append(format_module_path + '.%s')
            format_locations.reverse()
        locale = to_locale(lang)
        locales = [locale]
        if '_' in locale:
            locales.append(locale.split('_')[0])
        for location in format_locations:
            for loc in locales:
                try:
                    yield import_module('%s.formats' % (location % loc))
                except ImportError:
                    pass


def get_format_modules(lang=None, reverse=False):
    """
    Returns a list of the format modules found
    """
    if lang is None:
        lang = get_language()
    modules = _format_modules_cache.setdefault(lang, list(iter_format_modules(lang, settings.FORMAT_MODULE_PATH)))
    if reverse:
        return list(reversed(modules))
    return modules


def get_format(format_type, lang=None, use_l10n=None):
    """
    For a specific format type, returns the format for the current
    language (locale), defaults to the format in the settings.
    format_type is the name of the format, e.g. 'DATE_FORMAT'

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.
    """
    format_type = force_str(format_type)
    if use_l10n or (use_l10n is None and settings.USE_L10N):
        if lang is None:
            lang = get_language()
        cache_key = (format_type, lang)
        try:
            cached = _format_cache[cache_key]
            if cached is not None:
                return cached
            else:
                # Return the general setting by default
                return getattr(settings, format_type)
        except KeyError:
            for module in get_format_modules(lang):
                try:
                    val = getattr(module, format_type)
                    for iso_input in ISO_INPUT_FORMATS.get(format_type, ()):
                        if iso_input not in val:
                            if isinstance(val, tuple):
                                val = list(val)
                            val.append(iso_input)
                    _format_cache[cache_key] = val
                    return val
                except AttributeError:
                    pass
            _format_cache[cache_key] = None
    return getattr(settings, format_type)

get_format_lazy = lazy(get_format, six.text_type, list, tuple)


def date_format(value, format=None, use_l10n=None):
    """
    Formats a datetime.date or datetime.datetime object using a
    localizable format

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.
    """
    return dateformat.format(value, get_format(format or 'DATE_FORMAT', use_l10n=use_l10n))


def time_format(value, format=None, use_l10n=None):
    """
    Formats a datetime.time object using a localizable format

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.
    """
    return dateformat.time_format(value, get_format(format or 'TIME_FORMAT', use_l10n=use_l10n))


def number_format(value, decimal_pos=None, use_l10n=None, force_grouping=False):
    """
    Formats a numeric value using localization settings

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.
    """
    if use_l10n or (use_l10n is None and settings.USE_L10N):
        lang = get_language()
    else:
        lang = None
    return numberformat.format(
        value,
        get_format('DECIMAL_SEPARATOR', lang, use_l10n=use_l10n),
        decimal_pos,
        get_format('NUMBER_GROUPING', lang, use_l10n=use_l10n),
        get_format('THOUSAND_SEPARATOR', lang, use_l10n=use_l10n),
        force_grouping=force_grouping
    )


def localize(value, use_l10n=None):
    """
    Checks if value is a localizable type (date, number...) and returns it
    formatted as a string using current locale format.

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.
    """
    if isinstance(value, bool):
        return mark_safe(six.text_type(value))
    elif isinstance(value, (decimal.Decimal, float) + six.integer_types):
        return number_format(value, use_l10n=use_l10n)
    elif isinstance(value, datetime.datetime):
        return date_format(value, 'DATETIME_FORMAT', use_l10n=use_l10n)
    elif isinstance(value, datetime.date):
        return date_format(value, use_l10n=use_l10n)
    elif isinstance(value, datetime.time):
        return time_format(value, 'TIME_FORMAT', use_l10n=use_l10n)
    else:
        return value


def localize_input(value, default=None):
    """
    Checks if an input value is a localizable type and returns it
    formatted with the appropriate formatting string of the current locale.
    """
    if isinstance(value, (decimal.Decimal, float) + six.integer_types):
        return number_format(value)
    elif isinstance(value, datetime.datetime):
        value = datetime_safe.new_datetime(value)
        format = force_str(default or get_format('DATETIME_INPUT_FORMATS')[0])
        return value.strftime(format)
    elif isinstance(value, datetime.date):
        value = datetime_safe.new_date(value)
        format = force_str(default or get_format('DATE_INPUT_FORMATS')[0])
        return value.strftime(format)
    elif isinstance(value, datetime.time):
        format = force_str(default or get_format('TIME_INPUT_FORMATS')[0])
        return value.strftime(format)
    return value


def sanitize_separators(value):
    """
    Sanitizes a value according to the current decimal and
    thousand separator setting. Used with form field input.
    """
    if settings.USE_L10N and isinstance(value, six.string_types):
        parts = []
        decimal_separator = get_format('DECIMAL_SEPARATOR')
        if decimal_separator in value:
            value, decimals = value.split(decimal_separator, 1)
            parts.append(decimals)
        if settings.USE_THOUSAND_SEPARATOR:
            thousand_sep = get_format('THOUSAND_SEPARATOR')
            for replacement in set([
                    thousand_sep, unicodedata.normalize('NFKD', thousand_sep)]):
                value = value.replace(replacement, '')
        parts.append(value)
        value = '.'.join(reversed(parts))
    return value
