# These are versions of the functions in django.utils.translation.trans_real
# that don't actually do anything. This is purely for performance, so that
# settings.USE_I18N = False can use this module rather than trans_real.py.

from django.conf import settings
from django.utils.encoding import force_text


def ngettext(singular, plural, number):
    if number == 1:
        return singular
    return plural
ngettext_lazy = ngettext


def ungettext(singular, plural, number):
    return force_text(ngettext(singular, plural, number))


def pgettext(context, message):
    return ugettext(message)


def npgettext(context, singular, plural, number):
    return ungettext(singular, plural, number)


def activate(x):
    return None


def deactivate():
    return None


deactivate_all = deactivate


def get_language():
    return settings.LANGUAGE_CODE


def get_language_bidi():
    return settings.LANGUAGE_CODE in settings.LANGUAGES_BIDI


def check_for_language(x):
    return True


def gettext(message):
    return message


def ugettext(message):
    return force_text(gettext(message))

gettext_noop = gettext_lazy = _ = gettext


def to_locale(language):
    p = language.find('-')
    if p >= 0:
        return language[:p].lower() + '_' + language[p + 1:].upper()
    else:
        return language.lower()


def get_language_from_request(request, check_path=False):
    return settings.LANGUAGE_CODE


def get_language_from_path(request):
    return None
