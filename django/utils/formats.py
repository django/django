import decimal
import datetime

from django.conf import settings
from django.utils.translation import get_language, to_locale, check_for_language
from django.utils.importlib import import_module
from django.utils.encoding import smart_str
from django.utils import dateformat, numberformat, datetime_safe
from django.utils.safestring import mark_safe

# format_cache is a mapping from (format_type, lang) to the format string.
# By using the cache, it is possible to avoid running get_format_modules
# repeatedly.
_format_cache = {}
_format_modules_cache = {}

def iter_format_modules(lang):
    """
    Does the heavy lifting of finding format modules.
    """
    if check_for_language(lang) or settings.USE_L10N:
        format_locations = ['django.conf.locale.%s']
        if settings.FORMAT_MODULE_PATH:
            format_locations.append(settings.FORMAT_MODULE_PATH + '.%s')
            format_locations.reverse()
        locale = to_locale(lang)
        locales = set((locale, locale.split('_')[0]))
        for location in format_locations:
            for loc in locales:
                try:
                    yield import_module('.formats', location % loc)
                except ImportError:
                    pass

def get_format_modules(reverse=False):
    """
    Returns an iterator over the format modules found
    """
    lang = get_language()
    modules = _format_modules_cache.setdefault(lang, list(iter_format_modules(lang)))
    if reverse:
        modules.reverse()
    return modules

def get_format(format_type):
    """
    For a specific format type, returns the format for the current
    language (locale), defaults to the format in the settings.
    format_type is the name of the format, e.g. 'DATE_FORMAT'
    """
    format_type = smart_str(format_type)
    if settings.USE_L10N:
        cache_key = (format_type, get_language())
        try:
            return _format_cache[cache_key] or getattr(settings, format_type)
        except KeyError:
            for module in get_format_modules():
                try:
                    val = getattr(module, format_type)
                    _format_cache[cache_key] = val
                    return val
                except AttributeError:
                    pass
            _format_cache[cache_key] = None
    return getattr(settings, format_type)

def date_format(value, format=None):
    """
    Formats a datetime.date or datetime.datetime object using a
    localizable format
    """
    return dateformat.format(value, get_format(format or 'DATE_FORMAT'))

def time_format(value, format=None):
    """
    Formats a datetime.time object using a localizable format
    """
    return dateformat.time_format(value, get_format(format or 'TIME_FORMAT'))

def number_format(value, decimal_pos=None):
    """
    Formats a numeric value using localization settings
    """
    return numberformat.format(
        value,
        get_format('DECIMAL_SEPARATOR'),
        decimal_pos,
        get_format('NUMBER_GROUPING'),
        get_format('THOUSAND_SEPARATOR'),
    )

def localize(value):
    """
    Checks if value is a localizable type (date, number...) and returns it
    formatted as a string using current locale format
    """
    if isinstance(value, bool):
        return mark_safe(unicode(value))
    elif isinstance(value, (decimal.Decimal, float, int, long)):
        return number_format(value)
    elif isinstance(value, datetime.datetime):
        return date_format(value, 'DATETIME_FORMAT')
    elif isinstance(value, datetime.date):
        return date_format(value)
    elif isinstance(value, datetime.time):
        return time_format(value, 'TIME_FORMAT')
    else:
        return value

def localize_input(value, default=None):
    """
    Checks if an input value is a localizable type and returns it
    formatted with the appropriate formatting string of the current locale.
    """
    if isinstance(value, (decimal.Decimal, float, int, long)):
        return number_format(value)
    if isinstance(value, datetime.datetime):
        value = datetime_safe.new_datetime(value)
        format = smart_str(default or get_format('DATETIME_INPUT_FORMATS')[0])
        return value.strftime(format)
    elif isinstance(value, datetime.date):
        value = datetime_safe.new_date(value)
        format = smart_str(default or get_format('DATE_INPUT_FORMATS')[0])
        return value.strftime(format)
    elif isinstance(value, datetime.time):
        format = smart_str(default or get_format('TIME_INPUT_FORMATS')[0])
        return value.strftime(format)
    return value

def sanitize_separators(value):
    """
    Sanitizes a value according to the current decimal and
    thousand separator setting. Used with form field input.
    """
    if settings.USE_L10N:
        decimal_separator = get_format('DECIMAL_SEPARATOR')
        if isinstance(value, basestring):
            parts = []
            if decimal_separator in value:
                value, decimals = value.split(decimal_separator, 1)
                parts.append(decimals)
            if settings.USE_THOUSAND_SEPARATOR:
                parts.append(value.replace(get_format('THOUSAND_SEPARATOR'), ''))
            else:
                parts.append(value)
            value = '.'.join(reversed(parts))
    return value
