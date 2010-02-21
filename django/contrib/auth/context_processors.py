from django.core.context_processors import PermWrapper
from django.utils.functional import lazy, memoize, SimpleLazyObject
from django.contrib import messages

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
        'user': SimpleLazyObject(get_user),
        'messages': messages.get_messages(request),
        'perms':  lazy(lambda: PermWrapper(get_user()), PermWrapper)(),
    }
