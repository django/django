from django.conf import settings
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from ..checks.sessions import add_session_cookie_message, add_httponly_message


class CheckSessionCookieSecureTest(TestCase):
    @property
    def func(self):
        from ..checks.sessions import check_session_cookie_secure
        return check_session_cookie_secure

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[])
    def test_session_cookie_secure_with_installed_app(self):
        """
        Warns if SESSION_COOKIE_SECURE is off and "django.contrib.sessions" is
        in INSTALLED_APPS.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_session_cookie_message(
                    "You have 'django.contrib.sessions' in your INSTALLED_APPS, "
                    "but you have not set SESSION_COOKIE_SECURE to True."
                ),
                hint=None,
                id='secure.W010',
            )]
        )

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=[],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_with_middleware(self):
        """
        Warns if SESSION_COOKIE_SECURE is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE_CLASSES.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_session_cookie_message(
                    "You have 'django.contrib.sessions.middleware.SessionMiddleware' "
                    "in your MIDDLEWARE_CLASSES, but you have not set "
                    "SESSION_COOKIE_SECURE to True.",
                ),
                hint=None,
                id='secure.W011',
            )]
        )

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_both(self):
        """
        If SESSION_COOKIE_SECURE is off and we find both the session app and
        the middleware, we just provide one common warning.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_session_cookie_message("SESSION_COOKIE_SECURE is not set to True."),
                hint=None,
                id='secure.W012',
            )]
        )

    @override_settings(
        SESSION_COOKIE_SECURE=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_true(self):
        """
        If SESSION_COOKIE_SECURE is on, there's no warning about it.
        """
        self.assertEqual(self.func(None), [])


class CheckSessionCookieHttpOnlyTest(TestCase):
    @property
    def func(self):
        from ..checks.sessions import check_session_cookie_httponly
        return check_session_cookie_httponly

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[])
    def test_session_cookie_httponly_with_installed_app(self):
        """
        Warns if SESSION_COOKIE_HTTPONLY is off and "django.contrib.sessions"
        is in INSTALLED_APPS.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_httponly_message(
                    "You have 'django.contrib.sessions' in your INSTALLED_APPS, "
                    "but you have not set SESSION_COOKIE_HTTPONLY to True."
                ),
                hint=None,
                id='secure.W013',
            )]
        )

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=[],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_with_middleware(self):
        """
        Warns if SESSION_COOKIE_HTTPONLY is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE_CLASSES.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_httponly_message(
                    "You have 'django.contrib.sessions.middleware.SessionMiddleware' "
                    "in your MIDDLEWARE_CLASSES, but you have not set "
                    "SESSION_COOKIE_HTTPONLY to True."
                ),
                hint=None,
                id='secure.W014',
            )]
        )

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_both(self):
        """
        If SESSION_COOKIE_HTTPONLY is off and we find both the session app and
        the middleware, we just provide one common warning.
        """
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                add_httponly_message("SESSION_COOKIE_HTTPONLY is not set to True."),
                hint=None,
                id='secure.W015',
            )]
        )

    @override_settings(
        SESSION_COOKIE_HTTPONLY=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_true(self):
        """
        If SESSION_COOKIE_HTTPONLY is on, there's no warning about it.
        """
        self.assertEqual(self.func(None), [])


class CheckCSRFMiddlewareTest(TestCase):
    @property
    def func(self):
        from ..checks.csrf import check_csrf_middleware
        return check_csrf_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_csrf_middleware(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("You don't appear to be using Django's built-in "
                "cross-site request forgery protection via the middleware "
                "('django.middleware.csrf.CsrfViewMiddleware' is not in your "
                "MIDDLEWARE_CLASSES). Enabling the middleware is the safest approach "
                "to ensure you don't leave any holes."),
                hint=None,
                id='secure.W003',
            )]
        )

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"])
    def test_with_csrf_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckSecurityMiddlewareTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_security_middleware
        return check_security_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_security_middleware(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("You do not have 'django.contrib.secure.middleware.SecurityMiddleware' "
                "in your MIDDLEWARE_CLASSES so the SECURE_HSTS_SECONDS, "
                "SECURE_CONTENT_TYPE_NOSNIFF, "
                "SECURE_BROWSER_XSS_FILTER and SECURE_SSL_REDIRECT settings "
                "will have no effect."),
                hint=None,
                id='secure.W001',
            )]
        )

    @override_settings(
        MIDDLEWARE_CLASSES=["django.contrib.secure.middleware.SecurityMiddleware"])
    def test_with_security_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecurityTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_sts
        return check_sts

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_no_sts(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("You have not set a value for the SECURE_HSTS_SECONDS setting. "
                "If your entire site is served only over SSL, you may want to consider "
                "setting a value and enabling HTTP Strict Transport Security "
                "(see http://en.wikipedia.org/wiki/Strict_Transport_Security)."),
                hint=None,
                id='secure.W004',
            )]
        )

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_with_sts(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecuritySubdomainsTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_sts_include_subdomains
        return check_sts_include_subdomains

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_no_sts_subdomains(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
                "Without this, your site is potentially vulnerable to attack "
                "via an insecure connection to a subdomain."),
                hint=None,
                id='secure.W005',
            )]
        )

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_with_sts_subdomains(self):
        self.assertEqual(self.func(None), [])


class CheckXFrameOptionsMiddelwareTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_xframe_options_middleware
        return check_xframe_options_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_middleware_not_installed(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("You do not have "
                "'django.middleware.clickjacking.XFrameOptionsMiddleware ' in your "
                "MIDDLEWARE_CLASSES, so your pages will not be served with an "
                "'x-frame-options' header. "
                "Unless there is a good reason for your site to be served in a frame, "
                "you should consider enabling this header "
                "to help prevent clickjacking attacks."),
                hint=None,
                id='secure.W002',
            )]
        )

    @override_settings(MIDDLEWARE_CLASSES=["django.middleware.clickjacking.XFrameOptionsMiddleware"])
    def test_middleware_installed(self):
        self.assertEqual(self.func(None), [])


class CheckContentTypeNosniffTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_content_type_nosniff
        return check_content_type_nosniff

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
                "so your pages will not be served with an "
                "'x-content-type-options: nosniff' header. "
                "You should consider enabling this header to prevent the "
                "browser from identifying content types incorrectly."),
                hint=None,
                id='secure.W006',
            )]
        )

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_with_content_type_nosniff(self):
        self.assertEqual(self.func(None), [])


class CheckXssFilterTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_xss_filter
        return check_xss_filter

    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("Your SECURE_BROWSER_XSS_FILTER setting is not set to True, "
                "so your pages will not be served with an "
                "'x-xss-protection: 1; mode=block' header. "
                "You should consider enabling this header to activate the "
                "browser's XSS filtering and help prevent XSS attacks."),
                hint=None,
                id='secure.W007',
            )]
        )

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_with_xss_filter(self):
        self.assertEqual(self.func(None), [])


class CheckSSLRedirectTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_ssl_redirect
        return check_ssl_redirect

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_no_sts(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                ("Your SECURE_SSL_REDIRECT setting is not set to True. "
                "Unless your site should be available over both SSL and non-SSL "
                "connections, you may want to either set this setting True "
                "or configure a loadbalancer or reverse-proxy server "
                "to redirect all connections to HTTPS."),
                hint=None,
                id='secure.W008',
            )]
        )

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_with_sts(self):
        self.assertEqual(self.func(None), [])


class CheckSecretKeyTest(TestCase):
    @property
    def func(self):
        from ..checks.base import check_secret_key
        return check_secret_key

    @property
    def secret_key_error(self):
        return [checks.Warning(
            ("Your SECRET_KEY is either an empty string, non-existent, or has not "
            "enough characters. Please generate a long and random SECRET_KEY, "
            "otherwise many of Django's security-critical features will be "
            "vulnerable to attack."),
            hint=None,
            id='secure.W009',
        )]

    @override_settings(SECRET_KEY='awcetupav$#!^h9wTUAPCJWE&!T#``Ho;ta9w4tva')
    def test_okay_secret_key(self):
        self.assertEqual(self.func(None), [])

    @override_settings(SECRET_KEY='')
    def test_empty_secret_key(self):
        self.assertEqual(self.func(None), self.secret_key_error)

    @override_settings(SECRET_KEY=None)
    def test_missing_secret_key(self):
        del settings.SECRET_KEY
        self.assertEqual(self.func(None), self.secret_key_error)

    @override_settings(SECRET_KEY=None)
    def test_none_secret_key(self):
        self.assertEqual(self.func(None), self.secret_key_error)

    @override_settings(SECRET_KEY='bla bla')
    def test_low_entropy_secret_key(self):
        self.assertEqual(self.func(None), self.secret_key_error)


class ConfTest(TestCase):
    def test_no_fallback(self):
        """
        Accessing a setting without a default value raises in
        ImproperlyConfigured.
        """
        from ..conf import conf

        self.assertRaises(ImproperlyConfigured, getattr, conf, "HAS_NO_DEFAULT")

    def test_defaults(self):
        from ..conf import conf

        self.assertEqual(
            conf.defaults,
            {
                "SECURE_CHECKS": [
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
                ],
                "SECURE_HSTS_SECONDS": 0,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
                "SECURE_CONTENT_TYPE_NOSNIFF": False,
                "SECURE_BROWSER_XSS_FILTER": False,
                "SECURE_SSL_REDIRECT": False,
                "SECURE_SSL_HOST": None,
                "SECURE_REDIRECT_EXEMPT": [],
            }
        )
