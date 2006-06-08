class LazyUser(object):
    def __init__(self):
        self._user = None

    def __get__(self, request, obj_type=None):
        if self._user is None:
            from django.contrib.auth.models import User, AnonymousUser, SESSION_KEY
            try:
                user_id = request.session[SESSION_KEY]
                self._user = User.objects.get(pk=user_id)
            except (KeyError, User.DoesNotExist):
                self._user = AnonymousUser()
        return self._user

class AuthenticationMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        request.__class__.user = LazyUser()
        return None
