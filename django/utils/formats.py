import decimal
import datetime

from django.conf import settings
from django.utils.translation import get_language, to_locale, check_for_language
from django.utils.importlib import import_module
from django.utils import dateformat
from django.utils import numberformat

def get_format_modules():
    """
    Returns an iterator over the format modules found in the project and Django
    """
    modules = []
    if not check_for_language(get_language()):
        return modules
    locale = to_locale(get_language())
    if settings.FORMAT_MODULE_PATH:
        format_locations = [settings.FORMAT_MODULE_PATH + '.%s']
    else:
        format_locations = []
    format_locations.append('django.conf.locale.%s')
    for location in format_locations:
        for l in (locale, locale.split('_')[0]):
            try:
                mod = import_module('.formats', location % l)
            except ImportError:
                pass
            else:
                # Don't return duplicates
                if mod not in modules:
                    modules.append(mod)
    return modules

def get_format(format_type):
    """
    For a specific format type, returns the format for the current
    language (locale), defaults to the format in the settings.
    format_type is the name of the format, e.g. 'DATE_FORMAT'
    """
    if settings.USE_L10N:
        for module in get_format_modules():
            try:
                return getattr(module, format_type)
            except AttributeError:
                pass
    return getattr(settings, format_type)

def date_format(value, format=None):
    """
    Formats a datetime.date or datetime.datetime object using a
    localizable format
    """
    return dateformat.format(value, get_format(format or 'DATE_FORMAT'))

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

def localize(value, is_input=False):
    """
    Checks value, and if it has a localizable type (date,
    number...) it returns the value as a string using
    current locale format
    """
    if settings.USE_L10N:
        if isinstance(value, decimal.Decimal):
            return number_format(value)
        elif isinstance(value, float):
            return number_format(value)
        elif isinstance(value, int):
            return number_format(value)
        elif isinstance(value, datetime.datetime):
            if not is_input:
                return date_format(value, 'DATETIME_FORMAT')
            else:
                return value.strftime(get_format('DATETIME_INPUT_FORMATS')[0])
        elif isinstance(value, datetime.date):
            if not is_input:
                return date_format(value)
            else:
                return value.strftime(get_format('DATE_INPUT_FORMATS')[0])
        elif isinstance(value, datetime.time):
            if not is_input:
                return date_format(value, 'TIME_FORMAT')
            else:
                return value.strftime(get_format('TIME_INPUT_FORMATS')[0])
    return value

