"""
A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.

These are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""

from django.conf import settings

def auth(request):
    """
    Returns context variables required by apps that use Django's authentication
    system.

    If there is no 'user' attribute in the request, uses AnonymousUser (from
    django.contrib.auth).
    """
    if hasattr(request, 'user'):
        user = request.user
    else:
        from django.contrib.auth.models import AnonymousUser
        user = AnonymousUser()
    return {
        'user': user,
        'messages': user.get_and_delete_messages(),
        'perms': PermWrapper(user),
    }

def debug(request):
    "Returns context variables helpful for debugging."
    context_extras = {}
    if settings.DEBUG and request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
        context_extras['debug'] = True
        from django.db import connection
        context_extras['sql_queries'] = connection.queries
    return context_extras

def i18n(request):
    from django.utils import translation

    context_extras = {}
    context_extras['LANGUAGES'] = settings.LANGUAGES
    context_extras['LANGUAGE_CODE'] = translation.get_language()
    context_extras['LANGUAGE_BIDI'] = translation.get_language_bidi()

    return context_extras

def media(request):
    """
    Adds media-related context variables to the context.

    """
    return {'MEDIA_URL': settings.MEDIA_URL}

def request(request):
    return {'request': request}

# PermWrapper and PermLookupDict proxy the permissions system into objects that
# the template system can understand.

class PermLookupDict(object):
    def __init__(self, user, module_name):
        self.user, self.module_name = user, module_name

    def __repr__(self):
        return str(self.user.get_all_permissions())

    def __getitem__(self, perm_name):
        return self.user.has_perm("%s.%s" % (self.module_name, perm_name))

    def __nonzero__(self):
        return self.user.has_module_perms(self.module_name)

class PermWrapper(object):
    def __init__(self, user):
        self.user = user

    def __getitem__(self, module_name):
        return PermLookupDict(self.user, module_name)
        
    def __iter__(self):
        # I am large, I contain multitudes.
        raise TypeError("PermWrapper is not iterable.")
