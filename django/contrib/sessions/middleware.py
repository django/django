import time

from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.http import cookie_date

TEST_COOKIE_NAME = 'testcookie'
TEST_COOKIE_VALUE = 'worked'

class SessionMiddleware(object):

    def process_request(self, request):
        engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, None)
        request.session = engine.SessionStore(session_key)

    def process_response(self, request, response):
        # If request.session was modified, or if response.session was set, save
        # those changes and set a session cookie.
        try:
            accessed = request.session.accessed
            modified = request.session.modified
        except AttributeError:
            pass
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if modified or settings.SESSION_SAVE_EVERY_REQUEST:
                if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
                    max_age = None
                    expires = None
                else:
                    max_age = settings.SESSION_COOKIE_AGE
                    expires_time = time.time() + settings.SESSION_COOKIE_AGE
                    expires = cookie_date(expires_time)
                # Save the seesion data and refresh the client cookie.
                request.session.save()
                response.set_cookie(settings.SESSION_COOKIE_NAME,
                        request.session.session_key, max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None)

        return response
