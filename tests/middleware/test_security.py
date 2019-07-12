from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.test.utils import override_settings


class SecurityMiddlewareTest(SimpleTestCase):
    @property
    def middleware(self):
        from django.middleware.security import SecurityMiddleware
        return SecurityMiddleware()

    @property
    def secure_request_kwargs(self):
        return {"wsgi.url_scheme": "https"}

    def response(self, *args, headers=None, **kwargs):
        response = HttpResponse(*args, **kwargs)
        if headers:
            for k, v in headers.items():
                response[k] = v
        return response

    def process_response(self, *args, secure=False, request=None, **kwargs):
        request_kwargs = {}
        if secure:
            request_kwargs.update(self.secure_request_kwargs)
        if request is None:
            request = self.request.get("/some/url", **request_kwargs)
        ret = self.middleware.process_request(request)
        if ret:
            return ret
        return self.middleware.process_response(
            request, self.response(*args, **kwargs))

    request = RequestFactory()

    def process_request(self, method, *args, secure=False, **kwargs):
        if secure:
            kwargs.update(self.secure_request_kwargs)
        req = getattr(self.request, method.lower())(*args, **kwargs)
        return self.middleware.process_request(req)

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_on(self):
        """
        With SECURE_HSTS_SECONDS=3600, the middleware adds
        "Strict-Transport-Security: max-age=3600" to the response.
        """
        self.assertEqual(
            self.process_response(secure=True)["Strict-Transport-Security"],
            'max-age=3600',
        )

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_already_present(self):
        """
        The middleware will not override a "Strict-Transport-Security" header
        already present in the response.
        """
        response = self.process_response(
            secure=True,
            headers={"Strict-Transport-Security": "max-age=7200"})
        self.assertEqual(response["Strict-Transport-Security"], "max-age=7200")

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_only_if_secure(self):
        """
        The "Strict-Transport-Security" header is not added to responses going
        over an insecure connection.
        """
        self.assertNotIn("Strict-Transport-Security", self.process_response(secure=False))

    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_sts_off(self):
        """
        With SECURE_HSTS_SECONDS=0, the middleware does not add a
        "Strict-Transport-Security" header to the response.
        """
        self.assertNotIn("Strict-Transport-Security", self.process_response(secure=True))

    @override_settings(SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_sts_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        True, the middleware adds a "Strict-Transport-Security" header with the
        "includeSubDomains" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=600; includeSubDomains")

    @override_settings(SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_sts_no_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "Strict-Transport-Security" header without
        the "includeSubDomains" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=600")

    @override_settings(SECURE_HSTS_SECONDS=10886400, SECURE_HSTS_PRELOAD=True)
    def test_sts_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD True, the
        middleware adds a "Strict-Transport-Security" header with the "preload"
        directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=10886400; preload")

    @override_settings(SECURE_HSTS_SECONDS=10886400, SECURE_HSTS_INCLUDE_SUBDOMAINS=True, SECURE_HSTS_PRELOAD=True)
    def test_sts_subdomains_and_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero, SECURE_HSTS_INCLUDE_SUBDOMAINS and
        SECURE_HSTS_PRELOAD True, the middleware adds a "Strict-Transport-Security"
        header containing both the "includeSubDomains" and "preload" directives
        to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=10886400; includeSubDomains; preload")

    @override_settings(SECURE_HSTS_SECONDS=10886400, SECURE_HSTS_PRELOAD=False)
    def test_sts_no_preload(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_PRELOAD
        False, the middleware adds a "Strict-Transport-Security" header without
        the "preload" directive to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=10886400")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_on(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "X-Content-Type-Options: nosniff" header to the response.
        """
        self.assertEqual(self.process_response()["X-Content-Type-Options"], "nosniff")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_already_present(self):
        """
        The middleware will not override an "X-Content-Type-Options" header
        already present in the response.
        """
        response = self.process_response(secure=True, headers={"X-Content-Type-Options": "foo"})
        self.assertEqual(response["X-Content-Type-Options"], "foo")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_content_type_off(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "X-Content-Type-Options" header to the response.
        """
        self.assertNotIn("X-Content-Type-Options", self.process_response())

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_on(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to True, the middleware adds
        "s-xss-protection: 1; mode=block" header to the response.
        """
        self.assertEqual(self.process_response()["X-XSS-Protection"], "1; mode=block")

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_already_present(self):
        """
        The middleware will not override an "X-XSS-Protection" header
        already present in the response.
        """
        response = self.process_response(secure=True, headers={"X-XSS-Protection": "foo"})
        self.assertEqual(response["X-XSS-Protection"], "foo")

    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_xss_filter_off(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to False, the middleware does not
        add an "X-XSS-Protection" header to the response.
        """
        self.assertNotIn("X-XSS-Protection", self.process_response())

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_ssl_redirect_on(self):
        """
        With SECURE_SSL_REDIRECT True, the middleware redirects any non-secure
        requests to the https:// version of the same URL.
        """
        ret = self.process_request("get", "/some/url?query=string")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://testserver/some/url?query=string")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_no_redirect_ssl(self):
        """
        The middleware does not redirect secure requests.
        """
        ret = self.process_request("get", "/some/url", secure=True)
        self.assertIsNone(ret)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=["^insecure/"])
    def test_redirect_exempt(self):
        """
        The middleware does not redirect requests with URL path matching an
        exempt pattern.
        """
        ret = self.process_request("get", "/insecure/page")
        self.assertIsNone(ret)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_SSL_HOST="secure.example.com")
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
        With SECURE_SSL_REDIRECT False, the middleware does not redirect.
        """
        ret = self.process_request("get", "/some/url")
        self.assertIsNone(ret)
