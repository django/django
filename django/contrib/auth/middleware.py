class LazyUser(object):
    def __init__(self, session):
        self.session = session
        self._user = None

    def __get__(self, request, obj_type=None):
        if self._user is None:
            from django.contrib.auth.models import User, AnonymousUser, SESSION_KEY
            try:
                user_id = self.session[SESSION_KEY]
                self._user = User.objects.get(pk=user_id)
            except (KeyError, User.DoesNotExist):
                self._user = AnonymousUser()
            del self.session # We don't need to keep this around anymore.
        return self._user

class AuthenticationMiddleware:
    def process_request(self, request):
        from django.contrib.auth.models import SESSION_KEY
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        request.__class__.user = LazyUser(request.session)
        return None
