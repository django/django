from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings


class SecurityMiddlewareTest(TestCase):
    @property
    def middleware(self):
        from django.middleware.security import SecurityMiddleware
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
        With HSTS_SECONDS=3600, the middleware adds
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

    @override_settings(HSTS_SECONDS=3600)
    def test_sts_only_if_secure(self):
        """
        The "strict-transport-security" header is not added to responses going
        over an insecure connection.
        """
        self.assertNotIn("strict-transport-security", self.process_response(secure=False))

    @override_settings(HSTS_SECONDS=0)
    def test_sts_off(self):
        """
        With HSTS_SECONDS of 0, the middleware does not add a
        "strict-transport-security" header to the response.
        """
        self.assertNotIn("strict-transport-security", self.process_response(secure=True))

    @override_settings(
        SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_sts_include_subdomains(self):
        """
        With HSTS_SECONDS non-zero and HSTS_INCLUDE_SUBDOMAINS
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
        With HSTS_SECONDS non-zero and HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "strict-transport-security" header without
        the "includeSubDomains" tag to the response.
        """
        response = self.process_response(secure=True)
        self.assertEqual(response["strict-transport-security"], "max-age=600")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_on(self):
        """
        With CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "x-content-type-options: nosniff" header to the response.
        """
        self.assertEqual(self.process_response()["x-content-type-options"], "nosniff")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_already_present(self):
        """
        The middleware will not override an "x-content-type-options" header
        already present in the response.
        """
        response = self.process_response(secure=True, headers={"x-content-type-options": "foo"})
        self.assertEqual(response["x-content-type-options"], "foo")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_content_type_off(self):
        """
        With CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "x-content-type-options" header to the response.
        """
        self.assertNotIn("x-content-type-options", self.process_response())

    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_on(self):
        """
        With BROWSER_XSS_FILTER set to True, the middleware adds
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
        response = self.process_response(secure=True, headers={"x-xss-protection": "foo"})
        self.assertEqual(response["x-xss-protection"], "foo")

    @override_settings(BROWSER_XSS_FILTER=False)
    def test_xss_filter_off(self):
        """
        With BROWSER_XSS_FILTER set to False, the middleware does not add an
        "x-xss-protection" header to the response.
        """
        self.assertNotIn("x-xss-protection", self.process_response())

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_ssl_redirect_on(self):
        """
        With SSL_REDIRECT True, the middleware redirects any non-secure
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
        The middleware redirects to SSL_HOST if given.
        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://secure.example.com/some/url")

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_ssl_redirect_off(self):
        """
        With SSL_REDIRECT False, the middleware does no redirect.
        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret, None)
