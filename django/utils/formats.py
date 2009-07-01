from django.utils.importlib import import_module

def getformat_null(format_type):
    """
    For a specific format type, returns the default format as
    set on the settings.
    format_type is the name of the format, for example 'DATE_FORMAT'
    """
    from django.conf import settings
    return getattr(settings, format_type)

def getformat_real(format_type):
    """
    For a specific format type, returns the format for the
    current language (locale) defaulting to the format on settings.
    format_type is the name of the format, for example 'DATE_FORMAT'
    """
    from django.utils.translation import get_language
    import_formats = lambda s: import_module('.formats', 'django.conf.locale.%s' % s)
    tmp = import_formats('ca')
    format = None
    try:
        module = import_formats(get_language())
    except ImportError:
        pass
    else:
        try:
            format = getattr(module, format_type)
        except AttributeError:
            pass
    return format or getformat_null(format_type)

# getformat will just return the value on setings if
# we don't use i18n in our project
from django.conf import settings
if settings.USE_I18N and settings.USE_FORMAT_I18N:
    getformat = getformat_real
else:
    getformat = getformat_null

def date_and_time_format(value, format):
    import dateformat
    return dateformat.format(value, getformat('DATE_FORMAT'))

def date_format(value):
    import dateformat
    return dateformat.format(value, getformat('DATE_FORMAT'))

def datetime_format(value):
    import dateformat
    return dateformat.format(value, getformat('DATE_FORMAT'))

def time_format(value):
    import dateformat
    return dateformat.time_format(value, getformat('TIME_FORMAT'))

def number_format(value):
    import numberformat
    return numberformat.format(
        value,
        getformat('DECIMAL_SEPARATOR'),
        2, # TODO: decide how to set decimal positions later
        3, # TODO: get it from formats
        getformat('THOUSAND_SEPARATOR'),
    )

