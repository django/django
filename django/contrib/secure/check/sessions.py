from django.conf import settings


def check_session_cookie_secure():
    ret = set()
    if not settings.SESSION_COOKIE_SECURE:
        if _session_app():
            ret.add("SESSION_COOKIE_NOT_SECURE_APP_INSTALLED")
        if _session_middleware():
            ret.add("SESSION_COOKIE_NOT_SECURE_MIDDLEWARE")
        if len(ret) > 1:
            ret = set(["SESSION_COOKIE_NOT_SECURE"])
    return ret

check_session_cookie_secure.messages = {
    "SESSION_COOKIE_NOT_SECURE_APP_INSTALLED":
        ("You have 'django.contrib.sessions' in your INSTALLED_APPS, "
         "but you have not set SESSION_COOKIE_SECURE to True."),
    "SESSION_COOKIE_NOT_SECURE_MIDDLEWARE":
        ("You have 'django.contrib.sessions.middleware.SessionMiddleware' "
         "in your MIDDLEWARE_CLASSES, but you have not set "
         "SESSION_COOKIE_SECURE to True."),
    "SESSION_COOKIE_NOT_SECURE":
        "SESSION_COOKIE_SECURE is not set to True."
    }

for k, v in check_session_cookie_secure.messages.items():
    check_session_cookie_secure.messages[k] = (
        v + "Using a secure-only session cookie makes it more difficult for "
        "network traffic sniffers to hijack user sessions.")


def check_session_cookie_httponly():
    ret = set()
    if not settings.SESSION_COOKIE_HTTPONLY:
        if _session_app():
            ret.add("SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED")
        if _session_middleware():
            ret.add("SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE")
        if len(ret) > 1:
            ret = set(["SESSION_COOKIE_NOT_HTTPONLY"])
    return ret

check_session_cookie_httponly.messages = {
    "SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED":
        ("You have 'django.contrib.sessions' in your INSTALLED_APPS, "
         "but you have not set SESSION_COOKIE_HTTPONLY to True."),
    "SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE":
        ("You have 'django.contrib.sessions.middleware.SessionMiddleware' "
         "in your MIDDLEWARE_CLASSES, but you have not set "
         "SESSION_COOKIE_HTTPONLY to True."),
    "SESSION_COOKIE_NOT_HTTPONLY":
        "SESSION_COOKIE_HTTPONLY is not set to True."
    }

for k, v in check_session_cookie_httponly.messages.items():
    check_session_cookie_httponly.messages[k] = (
        v + "Using a HttpOnly session cookie makes it more difficult for "
        "cross-site scripting attacks to hijack user sessions.")


def _session_middleware():
    return ("django.contrib.sessions.middleware.SessionMiddleware" in
            settings.MIDDLEWARE_CLASSES)


def _session_app():
    return ("django.contrib.sessions" in settings.INSTALLED_APPS)
