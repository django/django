"""
A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.

These are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""

from django.conf import settings
from django.utils.functional import lazy, memoize, LazyObject

class ContextLazyObject(LazyObject):
    """
    A lazy object initialised from any function, useful for lazily
    adding things to the Context.

    Designed for compound objects of unknown type. For simple objects of known
    type, use django.utils.functional.lazy.
    """
    def __init__(self, func):
        """
        Pass in a callable that returns the actual value to be used
        """
        self.__dict__['_setupfunc'] = func
        # For some reason, we have to inline LazyObject.__init__ here to avoid
        # recursion
        self._wrapped = None

    def _setup(self):
        self._wrapped = self._setupfunc()

def auth(request):
    """
    Returns context variables required by apps that use Django's authentication
    system.

    If there is no 'user' attribute in the request, uses AnonymousUser (from
    django.contrib.auth).
    """
    # If we access request.user, request.session is accessed, which results in
    # 'Vary: Cookie' being sent in every request that uses this context
    # processor, which can easily be every request on a site if
    # TEMPLATE_CONTEXT_PROCESSORS has this context processor added.  This kills
    # the ability to cache.  So, we carefully ensure these attributes are lazy.
    # We don't use django.utils.functional.lazy() for User, because that
    # requires knowing the class of the object we want to proxy, which could
    # break with custom auth backends.  LazyObject is a less complete but more
    # flexible solution that is a good enough wrapper for 'User'.
    def get_user():
        if hasattr(request, 'user'):
            return request.user
        else:
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()

    return {
        'user': ContextLazyObject(get_user),
        'messages': lazy(memoize(lambda: get_user().get_and_delete_messages(), {}, 0), list)(),
        'perms':  lazy(lambda: PermWrapper(get_user()), PermWrapper)(),
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
