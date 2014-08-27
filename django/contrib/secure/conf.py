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
            raise ImproperlyConfigured("django.contrib.secure requires %s setting." % k)


conf = Configuration(
    SECURE_HSTS_SECONDS=0,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
    SECURE_CONTENT_TYPE_NOSNIFF=False,
    SECURE_BROWSER_XSS_FILTER=False,
    SECURE_SSL_REDIRECT=False,
    SECURE_SSL_HOST=None,
    SECURE_REDIRECT_EXEMPT=[],
    SECURE_CHECKS=[
        "django.contrib.secure.checks.csrf.check_csrf_middleware",
        "django.contrib.secure.checks.sessions.check_session_cookie_secure",
        "django.contrib.secure.checks.sessions.check_session_cookie_httponly",
        "django.contrib.secure.checks.base.check_security_middleware",
        "django.contrib.secure.checks.base.check_sts",
        "django.contrib.secure.checks.base.check_sts_include_subdomains",
        "django.contrib.secure.checks.base.check_xframe_options_middleware",
        "django.contrib.secure.checks.base.check_content_type_nosniff",
        "django.contrib.secure.checks.base.check_xss_filter",
        "django.contrib.secure.checks.base.check_ssl_redirect",
        "django.contrib.secure.checks.base.check_secret_key",
        ]
    )
