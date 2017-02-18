"""
A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.

These are referenced from the 'context_processors' option of the configuration
of a DjangoTemplates backend and used by RequestContext.
"""

from __future__ import unicode_literals

from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.encoding import smart_text
from django.utils.functional import SimpleLazyObject, lazy


def csrf(request):
    """
    Context processor that provides a CSRF token, or the string 'NOTPROVIDED' if
    it has not been provided by either a view decorator or the middleware
    """
    def _get_val():
        token = get_token(request)
        if token is None:
            # In order to be able to provide debugging info in the
            # case of misconfiguration, we use a sentinel value
            # instead of returning an empty dict.
            return 'NOTPROVIDED'
        else:
            return smart_text(token)

    return {'csrf_token': SimpleLazyObject(_get_val)}


def debug(request):
    """
    Returns context variables helpful for debugging.
    """
    context_extras = {}
    if settings.DEBUG and request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
        context_extras['debug'] = True
        from django.db import connection
        # Return a lazy reference that computes connection.queries on access,
        # to ensure it contains queries triggered after this function runs.
        context_extras['sql_queries'] = lazy(lambda: connection.queries, list)
    return context_extras


def i18n(request):
    from django.utils import translation

    context_extras = {}
    context_extras['LANGUAGES'] = settings.LANGUAGES
    context_extras['LANGUAGE_CODE'] = translation.get_language()
    context_extras['LANGUAGE_BIDI'] = translation.get_language_bidi()

    return context_extras


def tz(request):
    from django.utils import timezone

    return {'TIME_ZONE': timezone.get_current_timezone_name()}


def static(request):
    """
    Adds static-related context variables to the context.

    """
    return {'STATIC_URL': settings.STATIC_URL}


def media(request):
    """
    Adds media-related context variables to the context.

    """
    return {'MEDIA_URL': settings.MEDIA_URL}


def request(request):
    return {'request': request}
