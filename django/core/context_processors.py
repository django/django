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
    """
    return {
        'user': request.user,
        'messages': request.user.get_and_delete_messages(),
        'perms': PermWrapper(request.user),
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
    context_extras = {}
    context_extras['LANGUAGES'] = settings.LANGUAGES
    if hasattr(request, 'LANGUAGE_CODE'):
        context_extras['LANGUAGE_CODE'] = request.LANGUAGE_CODE
    else:
        context_extras['LANGUAGE_CODE'] = settings.LANGUAGE_CODE

    from django.utils import translation
    context_extras['LANGUAGE_BIDI'] = translation.get_language_bidi()

    return context_extras

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
