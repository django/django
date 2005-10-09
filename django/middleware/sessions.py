from django.conf.settings import SESSION_COOKIE_NAME, SESSION_COOKIE_AGE, SESSION_COOKIE_DOMAIN
from django.models.core import sessions
from django.utils.cache import patch_vary_headers
import datetime

TEST_COOKIE_NAME = 'testcookie'
TEST_COOKIE_VALUE = 'worked'

class SessionWrapper(object):
    def __init__(self, session_key):
        self.session_key = session_key
        self.modified = False

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    def get(self, key, default=None):
        return self._session.get(key, default)

    def set_test_cookie(self):
        self[TEST_COOKIE_NAME] = TEST_COOKIE_VALUE

    def test_cookie_worked(self):
        return self.get(TEST_COOKIE_NAME) == TEST_COOKIE_VALUE

    def delete_test_cookie(self):
        del self[TEST_COOKIE_NAME]

    def _get_session(self):
        # Lazily loads session from storage.
        try:
            return self._session_cache
        except AttributeError:
            if self.session_key is None:
                self._session_cache = {}
            else:
                try:
                    s = sessions.get_object(session_key__exact=self.session_key,
                        expire_date__gt=datetime.datetime.now())
                    self._session_cache = s.get_decoded()
                except sessions.SessionDoesNotExist:
                    self._session_cache = {}
                    # Set the session_key to None to force creation of a new
                    # key, for extra security.
                    self.session_key = None
            return self._session_cache

    _session = property(_get_session)

class SessionMiddleware:
    def process_request(self, request):
        request.session = SessionWrapper(request.COOKIES.get(SESSION_COOKIE_NAME, None))

    def process_response(self, request, response):
        # If request.session was modified, or if response.session was set, save
        # those changes and set a session cookie.
        patch_vary_headers(response, ('Cookie',))
        try:
            modified = request.session.modified
        except AttributeError:
            modified = False
        if modified:
            session_key = request.session.session_key or sessions.get_new_session_key()
            new_session = sessions.save(session_key, request.session._session,
                datetime.datetime.now() + datetime.timedelta(seconds=SESSION_COOKIE_AGE))
            response.set_cookie(SESSION_COOKIE_NAME, session_key,
                max_age=SESSION_COOKIE_AGE, domain=SESSION_COOKIE_DOMAIN)
        return response
