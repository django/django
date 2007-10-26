from django.conf import settings
from django.utils.cache import patch_vary_headers
from email.Utils import formatdate
import datetime
import time

TEST_COOKIE_NAME = 'testcookie'
TEST_COOKIE_VALUE = 'worked'

class SessionMiddleware(object):

    def process_request(self, request):
      engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
      request.session = engine.SessionStore(request.COOKIES.get(settings.SESSION_COOKIE_NAME, None))

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
                    rfcdate = formatdate(time.time() + settings.SESSION_COOKIE_AGE)

                    # Fixed length date must have '-' separation in the format
                    # DD-MMM-YYYY for compliance with Netscape cookie standard
                    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + \
                              datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE), "%a, %d-%b-%Y %H:%M:%S GMT")

                # Save the seesion data and refresh the client cookie.
                request.session.save()
                response.set_cookie(settings.SESSION_COOKIE_NAME,
                        request.session.session_key, max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None)

        return response
