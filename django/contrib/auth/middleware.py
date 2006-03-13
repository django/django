class UserWrapper(object):
    """
    Proxy to lazily load a user object.
    """
    def __init__(self, login):
        self._login = login
        self._cached_user = None

    def _get_user(self):
        from django.contrib.auth.models import User
        if not self._cached_user:
            self._cached_user = User.objects.get(pk=self._login)
        return self._cached_user

    _user = property(_get_user)

    def __getattr__(self, name):
        if name == '__setstate__': # slight hack to allow object to be unpickled
            return None 
        return getattr(self._user, name)

class AuthenticationMiddleware:
    def process_request(self, request):
        from django.contrib.auth.models import SESSION_KEY
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        try:
            user_id = request.session[SESSION_KEY]
            request.user = UserWrapper(user_id)
        except KeyError:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return None
