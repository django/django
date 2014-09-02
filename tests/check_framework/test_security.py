from django.conf import settings
from django.core import checks
from django.test import TestCase
from django.test.utils import override_settings

from django.core.checks.security.sessions import add_session_cookie_message, add_httponly_message


class CheckSessionCookieSecureTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.sessions import check_session_cookie_secure
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
                id='security.W010',
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
                id='security.W011',
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
                id='security.W012',
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
        from django.core.checks.security.sessions import check_session_cookie_httponly
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
                id='security.W013',
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
                id='security.W014',
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
                id='security.W015',
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
        from django.core.checks.security.csrf import check_csrf_middleware
        return check_csrf_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_csrf_middleware(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You don't appear to be using Django's built-in "
                "cross-site request forgery protection via the middleware "
                "('django.middleware.csrf.CsrfViewMiddleware' is not in your "
                "MIDDLEWARE_CLASSES). Enabling the middleware is the safest approach "
                "to ensure you don't leave any holes.",
                hint=None,
                id='security.W003',
            )]
        )

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"])
    def test_with_csrf_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckCSRFCookieSecureTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.csrf import check_csrf_cookie_secure
        return check_csrf_cookie_secure

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_SECURE=False)
    def test_with_csrf_cookie_secure_false(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You have 'django.middleware.csrf.CsrfViewMiddleware' in your "
                "MIDDLEWARE_CLASSES, but you have not set CSRF_COOKIE_SECURE to True. "
                "Using a secure-only CSRF cookie makes it more difficult for network "
                "traffic sniffers to steal the CSRF token.",
                hint=None,
                id='security.W016',
            )]
        )

    @override_settings(MIDDLEWARE_CLASSES=[], CSRF_COOKIE_SECURE=True)
    def test_with_csrf_cookie_secure_false_no_middleware(self):
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_SECURE=True)
    def test_with_csrf_cookie_secure_true(self):
        self.assertEqual(self.func(None), [])


class CheckCSRFCookieHttpOnlyTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.csrf import check_csrf_cookie_httponly
        return check_csrf_cookie_httponly

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_HTTPONLY=False)
    def test_with_csrf_cookie_httponly_false(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You have 'django.middleware.csrf.CsrfViewMiddleware' in your "
                "MIDDLEWARE_CLASSES, but you have not set CSRF_COOKIE_HTTPONLY to True. "
                "Using an HttpOnly CSRF cookie makes it more difficult for cross-site "
                "scripting attacks to steal the CSRF token.",
                hint=None,
                id='security.W017',
            )]
        )

    @override_settings(MIDDLEWARE_CLASSES=[], CSRF_COOKIE_HTTPONLY=True)
    def test_with_csrf_cookie_httponly_false_no_middleware(self):
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"],
        CSRF_COOKIE_HTTPONLY=True)
    def test_with_csrf_cookie_httponly_true(self):
        self.assertEqual(self.func(None), [])


class CheckSecurityMiddlewareTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_security_middleware
        return check_security_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_security_middleware(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You do not have 'django.middleware.security.SecurityMiddleware' "
                "in your MIDDLEWARE_CLASSES so the SECURE_HSTS_SECONDS, "
                "SECURE_CONTENT_TYPE_NOSNIFF, "
                "SECURE_BROWSER_XSS_FILTER and SECURE_SSL_REDIRECT settings "
                "will have no effect.",
                hint=None,
                id='security.W001',
            )]
        )

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.security.SecurityMiddleware"])
    def test_with_security_middleware(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecurityTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_sts
        return check_sts

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_no_sts(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You have not set a value for the SECURE_HSTS_SECONDS setting. "
                "If your entire site is served only over SSL, you may want to consider "
                "setting a value and enabling HTTP Strict Transport Security.",
                hint=None,
                id='security.W004',
            )]
        )

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_with_sts(self):
        self.assertEqual(self.func(None), [])


class CheckStrictTransportSecuritySubdomainsTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_sts_include_subdomains
        return check_sts_include_subdomains

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_no_sts_subdomains(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
                "Without this, your site is potentially vulnerable to attack "
                "via an insecure connection to a subdomain.",
                hint=None,
                id='security.W005',
            )]
        )

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_with_sts_subdomains(self):
        self.assertEqual(self.func(None), [])


class CheckXFrameOptionsMiddlewareTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xframe_options_middleware
        return check_xframe_options_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_middleware_not_installed(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You do not have "
                "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
                "MIDDLEWARE_CLASSES, so your pages will not be served with an "
                "'x-frame-options' header. "
                "Unless there is a good reason for your site to be served in a frame, "
                "you should consider enabling this header "
                "to help prevent clickjacking attacks.",
                hint=None,
                id='security.W002',
            )]
        )

    @override_settings(MIDDLEWARE_CLASSES=["django.middleware.clickjacking.XFrameOptionsMiddleware"])
    def test_middleware_installed(self):
        self.assertEqual(self.func(None), [])


class CheckXFrameOptionsDenyTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xframe_deny
        return check_xframe_deny

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.clickjacking.XFrameOptionsMiddleware"],
        X_FRAME_OPTIONS='SAMEORIGIN',
    )
    def test_x_frame_options_not_deny(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "You have "
                "'django.middleware.clickjacking.XFrameOptionsMiddleware' in your "
                "MIDDLEWARE_CLASSES, but X_FRAME_OPTIONS is not set to 'DENY'. "
                "The default is 'SAMEORIGIN' and unless there is a good reason for "
                "your site to serve other parts of itself in a frame, you should "
                "change this.",
                hint=None,
                id='security.W019',
            )]
        )

    @override_settings(MIDDLEWARE_CLASSES=[], X_FRAME_OPTIONS='SAMEORIGIN')
    def test_middleware_not_installed(self):
        self.assertEqual(self.func(None), [])

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.clickjacking.XFrameOptionsMiddleware"],
        X_FRAME_OPTIONS='DENY',
    )
    def test_xframe_deny(self):
        self.assertEqual(self.func(None), [])


class CheckContentTypeNosniffTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_content_type_nosniff
        return check_content_type_nosniff

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
                "so your pages will not be served with an "
                "'x-content-type-options: nosniff' header. "
                "You should consider enabling this header to prevent the "
                "browser from identifying content types incorrectly.",
                hint=None,
                id='security.W006',
            )]
        )

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_with_content_type_nosniff(self):
        self.assertEqual(self.func(None), [])


class CheckXssFilterTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_xss_filter
        return check_xss_filter

    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "Your SECURE_BROWSER_XSS_FILTER setting is not set to True, "
                "so your pages will not be served with an "
                "'x-xss-protection: 1; mode=block' header. "
                "You should consider enabling this header to activate the "
                "browser's XSS filtering and help prevent XSS attacks.",
                hint=None,
                id='security.W007',
            )]
        )

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_with_xss_filter(self):
        self.assertEqual(self.func(None), [])


class CheckSSLRedirectTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_ssl_redirect
        return check_ssl_redirect

    def test_no_ssl_redirect(self):
        self.assertEqual(
            self.func(None),
            [checks.Warning(
                "Your SECURE_SSL_REDIRECT setting is not set to True. "
                "Unless your site should be available over both SSL and non-SSL "
                "connections, you may want to either set this setting True "
                "or configure a load balancer or reverse-proxy server "
                "to redirect all connections to HTTPS.",
                hint=None,
                id='security.W008',
            )]
        )

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_with_ssl_redirect(self):
        self.assertEqual(self.func(None), [])


class CheckSecretKeyTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_secret_key
        return check_secret_key

    @property
    def secret_key_error(self):
        return [checks.Warning(
            "Your SECRET_KEY has less than 50 characters or less than 10 unique "
            "characters. Please generate a long and random SECRET_KEY, otherwise "
            "many of Django's security-critical features will be vulnerable to "
            "attack.",
            hint=None,
            id='security.W009',
        )]

    @override_settings(SECRET_KEY=('abcdefghijklmnopqrstuvwx' * 2) + 'ab')
    def test_okay_secret_key(self):
        self.assertEqual(len(settings.SECRET_KEY), 50)
        self.assertGreater(len(set(settings.SECRET_KEY)), 10)
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

    @override_settings(SECRET_KEY=('abcdefghijklmnopqrstuvwx' * 2) + 'a')
    def test_low_length_secret_key(self):
        self.assertEqual(len(settings.SECRET_KEY), 49)
        self.assertEqual(self.func(None), self.secret_key_error)

    @override_settings(SECRET_KEY='abcd' * 20)
    def test_low_entropy_secret_key(self):
        self.assertGreater(settings.SECRET_KEY, 50)
        self.assertLess(len(set(settings.SECRET_KEY)), 10)
        self.assertEqual(self.func(None), self.secret_key_error)


class CheckDebugTest(TestCase):
    @property
    def func(self):
        from django.core.checks.security.base import check_debug
        return check_debug

    @override_settings(DEBUG=True)
    def test_debug_true(self):
        self.assertEqual(self.func(None), [checks.Warning(
            "You shouldn't have DEBUG set to True in deployment.",
            hint=None,
            id='security.W018',
        )])

    @override_settings(DEBUG=False)
    def test_debug_false(self):
        self.assertEqual(self.func(None), [])
