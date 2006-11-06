class LazyUser(object):
    def __init__(self):
        self._user = None

    def __get__(self, request, obj_type=None):
        if self._user is None:
            from django.contrib.auth import get_user
            self._user = get_user(request)
        return self._user

class AuthenticationMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."
        request.__class__.user = LazyUser()
        return None
