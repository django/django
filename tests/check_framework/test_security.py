from django.conf import settings
from django.core.checks.security import base, csrf, sessions
from django.core.checks.utils import patch_middleware_message
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckSessionCookieSecureTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.sessions import check_session_cookie_secure
        return check_session_cookie_secure

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=[])
    def test_session_cookie_secure_with_installed_app(self):
        """
        Warn if SESSION_COOKIE_SECURE is off and "django.contrib.sessions" is
        in INSTALLED_APPS.
        """
        self.assertEqual(self.func(None), [sessions.W010])

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=None,
        MIDDLEWARE_CLASSES=[])
    def test_session_cookie_secure_with_installed_app_middleware_classes(self):
        self.assertEqual(self.func(None), [sessions.W010])

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=[],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_with_middleware(self):
        """
        Warn if SESSION_COOKIE_SECURE is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [sessions.W011])

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=[],
        MIDDLEWARE=None,
        MIDDLEWARE_CLASSES=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_with_middleware_middleware_classes(self):
        self.assertEqual(self.func(None), [patch_middleware_message(sessions.W011)])

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_both(self):
        """
        If SESSION_COOKIE_SECURE is off and we find both the session app and
        the middleware, provide one common warning.
        """
        self.assertEqual(self.func(None), [sessions.W012])

    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=None,
        MIDDLEWARE_CLASSES=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_both_middleware_classes(self):
        self.assertEqual(self.func(None), [sessions.W012])

    @override_settings(
        SESSION_COOKIE_SECURE=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_true(self):
        """
        If SESSION_COOKIE_SECURE is on, there's no warning about it.
        """
        self.assertEqual(self.func(None), [])


class CheckSessionCookieHttpOnlyTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.sessions import check_session_cookie_httponly
        return check_session_cookie_httponly

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=[])
    def test_session_cookie_httponly_with_installed_app(self):
        """
        Warn if SESSION_COOKIE_HTTPONLY is off and "django.contrib.sessions"
        is in INSTALLED_APPS.
        """
        self.assertEqual(self.func(None), [sessions.W013])

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=[],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_with_middleware(self):
        """
        Warn if SESSION_COOKIE_HTTPONLY is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [sessions.W014])

    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_both(self):
        """
        If SESSION_COOKIE_HTTPONLY is off and we find both the session app and
        the middleware, provide one common warning.
        """
        self.assertEqual(self.func(None), [sessions.W015])

    @override_settings(
        SESSION_COOKIE_HTTPONLY=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_true(self):
        """
        If SESSION_COOKIE_HTTPONLY is on, there's no warning about it.
        """
        self.assertEqual(self.func(None), [])


class CheckCSRFMiddlewareTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.csrf import check_csrf_middleware
        return check_csrf_middleware

    @override_settings(MIDDLEWARE=[], MIDDLEWARE_CLASSES=[])
    def test_no_csrf_middleware(self):
        """
        Warn if CsrfViewMiddleware isn't in MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [csrf.W003])

    @override_settings(
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"])
    def test_with_csrf_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckCSRFCookieSecureTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.csrf import check_csrf_cookie_secure
        return check_csrf_cookie_secure

    @override_settings(
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_SECURE=False)
    def test_with_csrf_cookie_secure_false(self):
        """
        Warn if CsrfViewMiddleware is in MIDDLEWARE but
        CSRF_COOKIE_SECURE isn't True.
        """
        self.assertEqual(self.func(None), [csrf.W016])

    @override_settings(MIDDLEWARE=[], MIDDLEWARE_CLASSES=[], CSRF_COOKIE_SECURE=False)
    def test_with_csrf_cookie_secure_false_no_middleware(self):
        """
        No warning if CsrfViewMiddleware isn't in MIDDLEWARE, even if
        CSRF_COOKIE_SECURE is False.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_SECURE=True)
    def test_with_csrf_cookie_secure_true(self):
        self.assertEqual(self.func(None), [])


class CheckCSRFCookieHttpOnlyTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.csrf import check_csrf_cookie_httponly
        return check_csrf_cookie_httponly

    @override_settings(
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_HTTPONLY=False)
    def test_with_csrf_cookie_httponly_false(self):
        """
        Warn if CsrfViewMiddleware is in MIDDLEWARE but
        CSRF_COOKIE_HTTPONLY isn't True.
        """
        self.assertEqual(self.func(None), [csrf.W017])

    @override_settings(MIDDLEWARE=[], MIDDLEWARE_CLASSES=[], CSRF_COOKIE_HTTPONLY=False)
    def test_with_csrf_cookie_httponly_false_no_middleware(self):
        """
        No warning if CsrfViewMiddleware isn't in MIDDLEWARE, even if
        CSRF_COOKIE_HTTPONLY is False.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_HTTPONLY=True)
    def test_with_csrf_cookie_httponly_true(self):
        self.assertEqual(self.func(None), [])


class CheckSecurityMiddlewareTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_security_middleware
        return check_security_middleware

    @override_settings(MIDDLEWARE=[])
    def test_no_security_middleware(self):
        """
        Warn if SecurityMiddleware isn't in MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [base.W001])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"])
    def test_with_security_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecurityTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_sts
        return check_sts

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_HSTS_SECONDS=0)
    def test_no_sts(self):
        """
        Warn if SECURE_HSTS_SECONDS isn't > 0.
        """
        self.assertEqual(self.func(None), [base.W004])

    @override_settings(
        MIDDLEWARE=[],
        SECURE_HSTS_SECONDS=0)
    def test_no_sts_no_middleware(self):
        """
        Don't warn if SECURE_HSTS_SECONDS isn't > 0 and SecurityMiddleware isn't
        installed.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_HSTS_SECONDS=3600)
    def test_with_sts(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecuritySubdomainsTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_sts_include_subdomains
        return check_sts_include_subdomains

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
        SECURE_HSTS_SECONDS=3600)
    def test_no_sts_subdomains(self):
        """
        Warn if SECURE_HSTS_INCLUDE_SUBDOMAINS isn't True.
        """
        self.assertEqual(self.func(None), [base.W005])

    @override_settings(
        MIDDLEWARE=[],
        SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
        SECURE_HSTS_SECONDS=3600)
    def test_no_sts_subdomains_no_middleware(self):
        """
        Don't warn if SecurityMiddleware isn't installed.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_SSL_REDIRECT=False,
        SECURE_HSTS_SECONDS=None)
    def test_no_sts_subdomains_no_seconds(self):
        """
        Don't warn if SECURE_HSTS_SECONDS isn't set.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_SECONDS=3600)
    def test_with_sts_subdomains(self):
        self.assertEqual(self.func(None), [])


class CheckXFrameOptionsMiddlewareTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xframe_options_middleware
        return check_xframe_options_middleware

    @override_settings(MIDDLEWARE=[])
    def test_middleware_not_installed(self):
        """
        Warn if XFrameOptionsMiddleware isn't in MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [base.W002])

    @override_settings(MIDDLEWARE=["django.middleware.clickjacking.XFrameOptionsMiddleware"])
    def test_middleware_installed(self):
        self.assertEqual(self.func(None), [])


class CheckXFrameOptionsDenyTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xframe_deny
        return check_xframe_deny

    @override_settings(
        MIDDLEWARE=["django.middleware.clickjacking.XFrameOptionsMiddleware"],
        X_FRAME_OPTIONS='SAMEORIGIN',
    )
    def test_x_frame_options_not_deny(self):
        """
        Warn if XFrameOptionsMiddleware is in MIDDLEWARE but
        X_FRAME_OPTIONS isn't 'DENY'.
        """
        self.assertEqual(self.func(None), [base.W019])

    @override_settings(MIDDLEWARE=[], X_FRAME_OPTIONS='SAMEORIGIN')
    def test_middleware_not_installed(self):
        """
        No error if XFrameOptionsMiddleware isn't in MIDDLEWARE even if
        X_FRAME_OPTIONS isn't 'DENY'.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.clickjacking.XFrameOptionsMiddleware"],
        X_FRAME_OPTIONS='DENY',
    )
    def test_xframe_deny(self):
        self.assertEqual(self.func(None), [])


class CheckContentTypeNosniffTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_content_type_nosniff
        return check_content_type_nosniff

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff(self):
        """
        Warn if SECURE_CONTENT_TYPE_NOSNIFF isn't True.
        """
        self.assertEqual(self.func(None), [base.W006])

    @override_settings(
        MIDDLEWARE=[],
        SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff_no_middleware(self):
        """
        Don't warn if SECURE_CONTENT_TYPE_NOSNIFF isn't True and
        SecurityMiddleware isn't in MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_with_content_type_nosniff(self):
        self.assertEqual(self.func(None), [])


class CheckXssFilterTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xss_filter
        return check_xss_filter

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter(self):
        """
        Warn if SECURE_BROWSER_XSS_FILTER isn't True.
        """
        self.assertEqual(self.func(None), [base.W007])

    @override_settings(
        MIDDLEWARE=[],
        SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter_no_middleware(self):
        """
        Don't warn if SECURE_BROWSER_XSS_FILTER isn't True and
        SecurityMiddleware isn't in MIDDLEWARE.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_BROWSER_XSS_FILTER=True)
    def test_with_xss_filter(self):
        self.assertEqual(self.func(None), [])


class CheckSSLRedirectTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_ssl_redirect
        return check_ssl_redirect

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_SSL_REDIRECT=False)
    def test_no_ssl_redirect(self):
        """
        Warn if SECURE_SSL_REDIRECT isn't True.
        """
        self.assertEqual(self.func(None), [base.W008])

    @override_settings(
        MIDDLEWARE=[],
        SECURE_SSL_REDIRECT=False)
    def test_no_ssl_redirect_no_middleware(self):
        """
        Don't warn if SECURE_SSL_REDIRECT is False and SecurityMiddleware isn't
        installed.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_SSL_REDIRECT=True)
    def test_with_ssl_redirect(self):
        self.assertEqual(self.func(None), [])


class CheckSecretKeyTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_secret_key
        return check_secret_key

    @override_settings(SECRET_KEY=('abcdefghijklmnopqrstuvwx' * 2) + 'ab')
    def test_okay_secret_key(self):
        self.assertEqual(len(settings.SECRET_KEY), base.SECRET_KEY_MIN_LENGTH)
        self.assertGreater(len(set(settings.SECRET_KEY)), base.SECRET_KEY_MIN_UNIQUE_CHARACTERS)
        self.assertEqual(self.func(None), [])

    @override_settings(SECRET_KEY='')
    def test_empty_secret_key(self):
        self.assertEqual(self.func(None), [base.W009])

    @override_settings(SECRET_KEY=None)
    def test_missing_secret_key(self):
        del settings.SECRET_KEY
        self.assertEqual(self.func(None), [base.W009])

    @override_settings(SECRET_KEY=None)
    def test_none_secret_key(self):
        self.assertEqual(self.func(None), [base.W009])

    @override_settings(SECRET_KEY=('abcdefghijklmnopqrstuvwx' * 2) + 'a')
    def test_low_length_secret_key(self):
        self.assertEqual(len(settings.SECRET_KEY), base.SECRET_KEY_MIN_LENGTH - 1)
        self.assertEqual(self.func(None), [base.W009])

    @override_settings(SECRET_KEY='abcd' * 20)
    def test_low_entropy_secret_key(self):
        self.assertGreater(len(settings.SECRET_KEY), base.SECRET_KEY_MIN_LENGTH)
        self.assertLess(len(set(settings.SECRET_KEY)), base.SECRET_KEY_MIN_UNIQUE_CHARACTERS)
        self.assertEqual(self.func(None), [base.W009])


class CheckDebugTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_debug
        return check_debug

    @override_settings(DEBUG=True)
    def test_debug_true(self):
        """
        Warn if DEBUG is True.
        """
        self.assertEqual(self.func(None), [base.W018])

    @override_settings(DEBUG=False)
    def test_debug_false(self):
        self.assertEqual(self.func(None), [])


class CheckAllowedHostsTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_allowed_hosts
        return check_allowed_hosts

    @override_settings(ALLOWED_HOSTS=[])
    def test_allowed_hosts_empty(self):
        self.assertEqual(self.func(None), [base.W020])

    @override_settings(ALLOWED_HOSTS=['.example.com', ])
    def test_allowed_hosts_set(self):
        self.assertEqual(self.func(None), [])
