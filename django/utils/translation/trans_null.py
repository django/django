# These are versions of the functions in django.utils.translation.trans_real
# that don't actually do anything. This is purely for performance, so that
# settings.USE_I18N = False can use this module rather than trans_real.py.

import warnings
from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe, SafeData

def ngettext(singular, plural, number):
    if number == 1: return singular
    return plural
ngettext_lazy = ngettext

def ungettext(singular, plural, number):
    return force_unicode(ngettext(singular, plural, number))

activate = lambda x: None
deactivate = deactivate_all = lambda: None
get_language = lambda: settings.LANGUAGE_CODE
get_language_bidi = lambda: settings.LANGUAGE_CODE in settings.LANGUAGES_BIDI
check_for_language = lambda x: True

# date formats shouldn't be used using gettext anymore. This
# is kept for backward compatibility
TECHNICAL_ID_MAP = {
    "DATE_WITH_TIME_FULL": settings.DATETIME_FORMAT,
    "DATE_FORMAT": settings.DATE_FORMAT,
    "DATETIME_FORMAT": settings.DATETIME_FORMAT,
    "TIME_FORMAT": settings.TIME_FORMAT,
    "YEAR_MONTH_FORMAT": settings.YEAR_MONTH_FORMAT,
    "MONTH_DAY_FORMAT": settings.MONTH_DAY_FORMAT,
}

def gettext(message):
    result = TECHNICAL_ID_MAP.get(message, message)
    if isinstance(message, SafeData):
        return mark_safe(result)
    return result

def ugettext(message):
    return force_unicode(gettext(message))

gettext_noop = gettext_lazy = _ = gettext

def to_locale(language):
    p = language.find('-')
    if p >= 0:
        return language[:p].lower()+'_'+language[p+1:].upper()
    else:
        return language.lower()

def get_language_from_request(request):
    return settings.LANGUAGE_CODE

# get_date_formats and get_partial_date_formats aren't used anymore by Django
# but are kept for backward compatibility.
def get_date_formats():
    warnings.warn(
        '`django.utils.translation.get_date_formats` is deprecated. '
        'Please update your code to use the new i18n aware formatting.',
        PendingDeprecationWarning
    )
    return settings.DATE_FORMAT, settings.DATETIME_FORMAT, settings.TIME_FORMAT

def get_partial_date_formats():
    warnings.warn(
        '`django.utils.translation.get_partial_date_formats` is deprecated. '
        'Please update your code to use the new i18n aware formatting.',
        PendingDeprecationWarning
    )
    return settings.YEAR_MONTH_FORMAT, settings.MONTH_DAY_FORMAT
