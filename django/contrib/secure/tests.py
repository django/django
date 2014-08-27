from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils.six import StringIO


class SecurityMiddlewareTest(TestCase):
    @property
    def middleware(self):
        from .middleware import SecurityMiddleware
        return SecurityMiddleware()

    @property
    def secure_request_kwargs(self):
        return {"wsgi.url_scheme": "https"}

    def response(self, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        response = HttpResponse(*args, **kwargs)
        for k, v in headers.items():
            response[k] = v
        return response

    def process_response(self, *args, **kwargs):
        request_kwargs = {}
        if kwargs.pop("secure", False):
            request_kwargs.update(self.secure_request_kwargs)
        request = (kwargs.pop("request", None) or
                   self.request.get("/some/url", **request_kwargs))
        ret = self.middleware.process_request(request)
        if ret:
            return ret
        return self.middleware.process_response(
            request, self.response(*args, **kwargs))

    request = RequestFactory()

    def process_request(self, method, *args, **kwargs):
        if kwargs.pop("secure", False):
            kwargs.update(self.secure_request_kwargs)
        req = getattr(self.request, method.lower())(*args, **kwargs)
        return self.middleware.process_request(req)

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_on(self):
        """
        With SECURE_HSTS_SECONDS=3600, the middleware adds
        "strict-transport-security: max-age=3600" to the response.
        """
        self.assertEqual(
            self.process_response(secure=True)["strict-transport-security"],
            "max-age=3600")

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_already_present(self):
        """
        The middleware will not override a "strict-transport-security" header
        already present in the response.

        """
        response = self.process_response(
            secure=True,
            headers={"strict-transport-security": "max-age=7200"})
        self.assertEqual(response["strict-transport-security"], "max-age=7200")

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_only_if_secure(self):
        """
        The "strict-transport-security" header is not added to responses going
        over an insecure connection.
        """
        self.assertFalse(
            "strict-transport-security" in self.process_response(secure=False))

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_sts_off(self):
        """
        With SECURE_HSTS_SECONDS of 0, the middleware does not add a
        "strict-transport-security" header to the response.
        """
        self.assertFalse(
            "strict-transport-security" in self.process_response(secure=True))

    @override_settings(
        SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_sts_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        True, the middleware adds a "strict-transport-security" header with the
        "includeSubDomains" tag to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response["strict-transport-security"],
            "max-age=600; includeSubDomains",
            )

    @override_settings(
        SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_sts_no_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "strict-transport-security" header without
        the "includeSubDomains" tag to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["strict-transport-security"], "max-age=600")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_on(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "x-content-type-options: nosniff" header to the response.
        """
        self.assertEqual(
            self.process_response()["x-content-type-options"],
            "nosniff")

    @override_settings(SECURE_CONTENT_TYPE_NO_SNIFF=True)
    def test_content_type_already_present(self):
        """
        The middleware will not override an "x-content-type-options" header
        already present in the response.
        """
        response = self.process_response(
            secure=True,
            headers={"x-content-type-options": "foo"})
        self.assertEqual(response["x-content-type-options"], "foo")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_content_type_off(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "x-content-type-options" header to the response.
        """
        self.assertFalse("x-content-type-options" in self.process_response())

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_on(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to True, the middleware adds
        "s-xss-protection: 1; mode=block" header to the response.
        """
        self.assertEqual(
            self.process_response()["x-xss-protection"],
            "1; mode=block")

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_already_present(self):
        """
        The middleware will not override an "x-xss-protection" header
        already present in the response.
        """
        response = self.process_response(
            secure=True,
            headers={"x-xss-protection": "foo"})
        self.assertEqual(response["x-xss-protection"], "foo")

    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_xss_filter_off(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to False, the middleware does not add an
        "x-xss-protection" header to the response.
        """
        self.assertFalse("x-xss-protection" in self.process_response())

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_ssl_redirect_on(self):
        """
        With SECURE_SSL_REDIRECT True, the middleware redirects any non-secure
        requests to the https:// version of the same URL.
        """
        ret = self.process_request("get", "/some/url?query=string")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(
            ret["Location"], "https://testserver/some/url?query=string")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_no_redirect_ssl(self):
        """
        The middleware does not redirect secure requests.
        """
        ret = self.process_request("get", "/some/url", secure=True)
        self.assertEqual(ret, None)

    @override_settings(
        SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=["^insecure/"])
    def test_redirect_exempt(self):
        """
        The middleware does not redirect requests with URL path matching an
        exempt pattern.
        """
        ret = self.process_request("get", "/insecure/page")
        self.assertEqual(ret, None)

    @override_settings(
        SECURE_SSL_REDIRECT=True, SECURE_SSL_HOST="secure.example.com")
    def test_redirect_ssl_host(self):
        """
        The middleware redirects to SECURE_SSL_HOST if given.
        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://secure.example.com/some/url")

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_ssl_redirect_off(self):
        """
        With SECURE_SSL_REDIRECT False, the middleware does no redirect.
        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret, None)


class ProxySecurityMiddlewareTest(SecurityMiddlewareTest):
    """
    Test that SecurityMiddleware behaves the same even if our "secure request"
    indicator is a proxy header.
    """
    def setUp(self):
        self.override = override_settings(
            SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTOCOL", "https"))

        self.override.enable()

    def tearDown(self):
        self.override.disable()

    @property
    def secure_request_kwargs(self):
        return {"HTTP_X_FORWARDED_PROTOCOL": "https"}

    def test_is_secure(self):
        """
        SecurityMiddleware patches request.is_secure() to report ``True`` even
        with a proxy-header secure request.

        """
        request = self.request.get("/some/url", **self.secure_request_kwargs)
        self.middleware.process_request(request)

        self.assertEqual(request.is_secure(), True)


def fake_test():
    return set(["SOME_WARNING"])

fake_test.messages = {
    "SOME_WARNING": "This is the warning message."
    }


def nomsg_test():
    return set(["OTHER WARNING"])


def passing_test():
    return []


class RunChecksTest(TestCase):
    @property
    def func(self):
        from .check import run_checks
        return run_checks

    @override_settings(
        SECURE_CHECKS=[
            "django.contrib.secure.tests.fake_test",
            "django.contrib.secure.tests.nomsg_test"])
    def test_returns_warnings(self):
        self.assertEqual(self.func(), set(["SOME_WARNING", "OTHER WARNING"]))


class CheckSettingsCommandTest(TestCase):
    def call(self, **options):
        stdout = options.setdefault("stdout", StringIO())
        stderr = options.setdefault("stderr", StringIO())

        call_command("checksecure", **options)

        stderr.seek(0)
        stdout.seek(0)

        return stdout.read(), stderr.read()

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.fake_test"])
    def test_prints_messages(self):
        stdout, stderr = self.call()
        self.assertTrue("This is the warning message." in stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.nomsg_test"])
    def test_prints_code_if_no_message(self):
        stdout, stderr = self.call()
        self.assertTrue("OTHER WARNING" in stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.fake_test"])
    def test_prints_code_if_verbosity_0(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertTrue("SOME_WARNING" in stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.fake_test"])
    def test_prints_check_names(self):
        stdout, stderr = self.call()
        self.assertTrue("django.contrib.secure.tests.fake_test" in stdout)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.fake_test"])
    def test_no_verbosity(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertEqual(stdout, "")

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.passing_test"])
    def test_all_clear(self):
        stdout, stderr = self.call()
        self.assertTrue("All clear!" in stdout)


class CheckSessionCookieSecureTest(TestCase):
    @property
    def func(self):
        from .check.sessions import check_session_cookie_secure
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
            self.func(), set(["SESSION_COOKIE_NOT_SECURE_APP_INSTALLED"]))

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
            self.func(), set(["SESSION_COOKIE_NOT_SECURE_MIDDLEWARE"]))

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
            self.func(), set(["SESSION_COOKIE_NOT_SECURE"]))

    @override_settings(
        SESSION_COOKIE_SECURE=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_true(self):
        """
        If SESSION_COOKIE_SECURE is on, there's no warning about it.
        """
        self.assertEqual(self.func(), set())


class CheckSessionCookieHttpOnlyTest(TestCase):
    @property
    def func(self):
        from .check.sessions import check_session_cookie_httponly
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
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED"]))

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
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE"]))

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
        self.assertTrue(
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY"]))

    @override_settings(
        SESSION_COOKIE_HTTPONLY=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_true(self):
        """
        If SESSION_COOKIE_HTTPONLY is on, there's no warning about it.
        """
        self.assertEqual(self.func(), set())


class CheckCSRFMiddlewareTest(TestCase):
    @property
    def func(self):
        from .check.csrf import check_csrf_middleware
        return check_csrf_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_csrf_middleware(self):
        self.assertEqual(
            self.func(), set(["CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED"]))

    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"])
    def test_with_csrf_middleware(self):
        self.assertEqual(self.func(), set())


class CheckSecurityMiddlewareTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_security_middleware
        return check_security_middleware

    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_security_middleware(self):
        self.assertEqual(
            self.func(), set(["SECURITY_MIDDLEWARE_NOT_INSTALLED"]))

    @override_settings(
        MIDDLEWARE_CLASSES=["django.contrib.secure.middleware.SecurityMiddleware"])
    def test_with_security_middleware(self):
        self.assertEqual(self.func(), set())


class CheckStrictTransportSecurityTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_sts
        return check_sts

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_no_sts(self):
        self.assertEqual(
            self.func(), set(["STRICT_TRANSPORT_SECURITY_NOT_ENABLED"]))

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_with_sts(self):
        self.assertEqual(self.func(), set())


class CheckStrictTransportSecuritySubdomainsTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_sts_include_subdomains
        return check_sts_include_subdomains

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_no_sts_subdomains(self):
        self.assertEqual(
            self.func(), set(["STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS"]))

    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_with_sts_subdomains(self):
        self.assertEqual(self.func(), set())


# TODO: replace with XFrameOptionsMiddleware
#class CheckFrameDenyTest(TestCase):
#    @property
#    def func(self):
#        from .check.djangosecure import check_frame_deny
#        return check_frame_deny

#    @override_settings(SECURE_FRAME_DENY=False)
#    def test_no_frame_deny(self):
#        self.assertEqual(
#            self.func(), set(["FRAME_DENY_NOT_ENABLED"]))

#    @override_settings(SECURE_FRAME_DENY=True)
#    def test_with_frame_deny(self):
#        self.assertEqual(self.func(), set())


class CheckContentTypeNosniffTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_content_type_nosniff
        return check_content_type_nosniff

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff(self):
        self.assertEqual(
            self.func(), set(["CONTENT_TYPE_NOSNIFF_NOT_ENABLED"]))

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_with_content_type_nosniff(self):
        self.assertEqual(self.func(), set())


class CheckXssFilterTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_xss_filter
        return check_xss_filter

    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter(self):
        self.assertEqual(
            self.func(), set(["BROWSER_XSS_FILTER_NOT_ENABLED"]))

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_with_xss_filter(self):
        self.assertEqual(self.func(), set())


class CheckSSLRedirectTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_ssl_redirect
        return check_ssl_redirect

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_no_sts(self):
        self.assertEqual(
            self.func(), set(["SSL_REDIRECT_NOT_ENABLED"]))

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_with_sts(self):
        self.assertEqual(self.func(), set())


class CheckSecretKeyTest(TestCase):
    @property
    def func(self):
        from .check.djangosecure import check_secret_key
        return check_secret_key

    @override_settings(SECRET_KEY='awcetupav$#!^h9wTUAPCJWE&!T#``Ho;ta9w4tva')
    def test_okay_secret_key(self):
        self.assertEqual(self.func(), set())

    @override_settings(SECRET_KEY='')
    def test_empty_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))

    @override_settings(SECRET_KEY=None)
    def test_missing_secret_key(self):
        del settings.SECRET_KEY
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))

    @override_settings(SECRET_KEY=None)
    def test_none_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))

    @override_settings(SECRET_KEY='bla bla')
    def test_low_entropy_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))


class ConfTest(TestCase):
    def test_no_fallback(self):
        """
        Accessing a setting without a default value raises in
        ImproperlyConfigured.
        """
        from .conf import conf

        self.assertRaises(ImproperlyConfigured, getattr, conf, "HAS_NO_DEFAULT")

    def test_defaults(self):
        from .conf import conf

        self.assertEqual(
            conf.defaults,
            {
                "SECURE_CHECKS": [
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
                ],
                "SECURE_HSTS_SECONDS": 0,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
                "SECURE_CONTENT_TYPE_NOSNIFF": False,
                "SECURE_BROWSER_XSS_FILTER": False,
                "SECURE_SSL_REDIRECT": False,
                "SECURE_SSL_HOST": None,
                "SECURE_REDIRECT_EXEMPT": [],
                "SECURE_PROXY_SSL_HEADER": None,
            }
        )
