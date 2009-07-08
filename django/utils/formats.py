import decimal
import datetime

from django.conf import settings
from django.utils.translation import get_language
from django.utils.importlib import import_module
from django.utils import dateformat
from django.utils import numberformat 

def getformat_null(format_type):
    """
    For a specific format type, returns the default format as
    set on the settings.
    format_type is the name of the format, for example 'DATE_FORMAT'
    """
    return getattr(settings, format_type)

def getformat_real(format_type):
    """
    For a specific format type, returns the format for the
    current language (locale) defaulting to the format on settings.
    format_type is the name of the format, for example 'DATE_FORMAT'
    """
    import_formats = lambda s: import_module('.formats', 'django.conf.locale.%s' % s)
    module = format = None
    if settings.FORMAT_MODULE_PATH:
        try:
            module = import_module('.formats', '%s.%s' % (settings.FORMAT_MODULE_PATH, get_language()))
        except ImportError:
            pass

    if not module:
        try:
            module = import_module('.formats', 'django.conf.locale.%s' % get_language())
        except ImportError:
            pass

    if module:
        try:
            format = getattr(module, format_type)
        except AttributeError:
            pass
    return format or getformat_null(format_type)

# getformat will just return the value on setings if
# we don't use i18n in our project
if settings.USE_I18N and settings.USE_FORMAT_I18N:
    getformat = getformat_real
else:
    getformat = getformat_null

def date_format(value, format=None):
    """
    Formats a datetime.date or datetime.datetime object using a
    localizable format
    """
    return dateformat.format(value, getformat(format or 'DATE_FORMAT'))

def number_format(value, decimal_pos=None):
    """
    Formats a numeric value using localization settings
    """
    return numberformat.format(
        value,
        getformat('DECIMAL_SEPARATOR'),
        decimal_pos,
        getformat('NUMBER_GROUPING'),
        getformat('THOUSAND_SEPARATOR'),
    )

def localize(value):
    """
    Checks value, and if it has a localizable type (date,
    number...) it returns the value as a string using
    current locale format
    """
    if settings.USE_I18N and settings.USE_FORMAT_I18N:
        if isinstance(value, decimal.Decimal):
            return number_format(value)
        elif isinstance(value, float):
            return number_format(value)
        elif isinstance(value, int):
            return number_format(value)
        elif isinstance(value, datetime.datetime):
            return date_format(value, 'DATETIME_FORMAT')
        elif isinstance(value, datetime.date):
            return date_format(value)
    return value

