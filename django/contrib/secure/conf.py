from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class Configuration(object):
    def __init__(self, **kwargs):
        self.defaults = kwargs

    def __getattr__(self, k):
        try:
            return getattr(settings, k)
        except AttributeError:
            if k in self.defaults:
                return self.defaults[k]
            raise ImproperlyConfigured("django-secure requires %s setting." % k)


conf = Configuration(
    SECURE_HSTS_SECONDS=0,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
    SECURE_CONTENT_TYPE_NOSNIFF=False,
    SECURE_BROWSER_XSS_FILTER=False,
    SECURE_SSL_REDIRECT=False,
    SECURE_SSL_HOST=None,
    SECURE_REDIRECT_EXEMPT=[],
    SECURE_PROXY_SSL_HEADER=None,
    SECURE_CHECKS=[
        "django.contrib.secure.check.csrf.check_csrf_middleware",
        "django.contrib.secure.check.sessions.check_session_cookie_secure",
        "django.contrib.secure.check.sessions.check_session_cookie_httponly",
        "django.contrib.secure.check.djangosecure.check_security_middleware",
        "django.contrib.secure.check.djangosecure.check_sts",
        "django.contrib.secure.check.djangosecure.check_sts_include_subdomains",
        "django.contrib.secure.check.djangosecure.check_frame_deny",
        "django.contrib.secure.check.djangosecure.check_content_type_nosniff",
        "django.contrib.secure.check.djangosecure.check_xss_filter",
        "django.contrib.secure.check.djangosecure.check_ssl_redirect",
        "django.contrib.secure.check.djangosecure.check_secret_key",
        ]
    )
