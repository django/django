# These are versions of the functions in django.utils.translation.trans_real
# that don't actually do anything. This is purely for performance, so that
# settings.USE_I18N = False can use this module rather than trans_real.py.

from django.conf import settings

def ngettext(singular, plural, number):
    if number == 1: return singular
    return plural
ngettext_lazy = ngettext

gettext = gettext_noop = gettext_lazy = _ = lambda x: x
string_concat = lambda *strings: ''.join([str(el) for el in strings])
activate = lambda x: None
deactivate = install = lambda: None
get_language = lambda: settings.LANGUAGE_CODE
get_language_bidi = lambda: settings.LANGUAGE_CODE in settings.LANGUAGES_BIDI
get_date_formats = lambda: (settings.DATE_FORMAT, settings.DATETIME_FORMAT, settings.TIME_FORMAT)
get_partial_date_formats = lambda: (settings.YEAR_MONTH_FORMAT, settings.MONTH_DAY_FORMAT)
check_for_language = lambda x: True

def to_locale(language):
    p = language.find('-')
    if p >= 0:
        return language[:p].lower()+'_'+language[p+1:].upper()
    else:
        return language.lower()

def get_language_from_request(request):
    return settings.LANGUAGE_CODE
