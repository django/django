"""
Testing using the Test Client

The test client is a class that can act like a simple
browser for testing purposes.

It allows the user to compose GET and POST requests, and
obtain the response that the server gave to those requests.
The server Response objects are annotated with the details
of the contexts and templates that were rendered during the
process of serving the request.

``Client`` objects are stateful - they will retain cookie (and
thus session) details for the lifetime of the ``Client`` instance.

This is not intended as a replacement for Twill, Selenium, or
other browser automation frameworks - it is here to allow
testing against the contexts and templates produced by a view,
rather than the HTML rendered to the end-user.

"""
import itertools
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.http import HttpResponse, HttpResponseNotAllowed
from django.test import (
    AsyncRequestFactory,
    Client,
    RequestFactory,
    SimpleTestCase,
    TestCase,
    modify_settings,
    override_settings,
)
from django.urls import reverse_lazy
from django.utils.decorators import async_only_middleware

from .views import TwoArgException, get_view, post_view, trace_view


def middleware_urlconf(get_response):
    def middleware(request):
        request.urlconf = "test_client.urls_middleware_urlconf"
        return get_response(request)

    return middleware


@async_only_middleware
def async_middleware_urlconf(get_response):
    async def middleware(request):
        request.urlconf = "test_client.urls_middleware_urlconf"
        return await get_response(request)

    return middleware


@override_settings(ROOT_URLCONF="test_client.urls")
class ClientTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username="testclient", password="password")
        cls.u2 = User.objects.create_user(
            username="inactive", password="password", is_active=False
        )

    def test_get_view(self):
        "GET a view"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        data = {"var": "\xf2"}
        response = self.client.get("/get_view/", data)

        # Check some response details
        self.assertContains(response, "This is a test")
        self.assertEqual(response.context["var"], "\xf2")
        self.assertEqual(response.templates[0].name, "GET Template")

    def test_query_string_encoding(self):
        # WSGI requires latin-1 encoded strings.
        response = self.client.get("/get_view/?var=1\ufffd")
        self.assertEqual(response.context["var"], "1\ufffd")

    def test_get_data_none(self):
        msg = (
            "Cannot encode None for key 'value' in a query string. Did you "
            "mean to pass an empty string or omit the value?"
        )
        with self.assertRaisesMessage(TypeError, msg):
            self.client.get("/get_view/", {"value": None})

    def test_get_post_view(self):
        "GET a view that normally expects POSTs"
        response = self.client.get("/post_view/", {})

        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "Empty GET Template")
        self.assertTemplateUsed(response, "Empty GET Template")
        self.assertTemplateNotUsed(response, "Empty POST Template")

    def test_empty_post(self):
        "POST an empty dictionary to a view"
        response = self.client.post("/post_view/", {})

        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "Empty POST Template")
        self.assertTemplateNotUsed(response, "Empty GET Template")
        self.assertTemplateUsed(response, "Empty POST Template")

    def test_post(self):
        "POST some data to a view"
        post_data = {"value": 37}
        response = self.client.post("/post_view/", post_data)

        # Check some response details
        self.assertContains(response, "Data received")
        self.assertEqual(response.context["data"], "37")
        self.assertEqual(response.templates[0].name, "POST Template")

    def test_post_data_none(self):
        msg = (
            "Cannot encode None for key 'value' as POST data. Did you mean "
            "to pass an empty string or omit the value?"
        )
        with self.assertRaisesMessage(TypeError, msg):
            self.client.post("/post_view/", {"value": None})

    def test_json_serialization(self):
        """The test client serializes JSON data."""
        methods = ("post", "put", "patch", "delete")
        tests = (
            ({"value": 37}, {"value": 37}),
            ([37, True], [37, True]),
            ((37, False), [37, False]),
        )
        for method in methods:
            with self.subTest(method=method):
                for data, expected in tests:
                    with self.subTest(data):
                        client_method = getattr(self.client, method)
                        method_name = method.upper()
                        response = client_method(
                            "/json_view/", data, content_type="application/json"
                        )
                        self.assertContains(response, "Viewing %s page." % method_name)
                        self.assertEqual(response.context["data"], expected)

    def test_json_encoder_argument(self):
        """The test Client accepts a json_encoder."""
        mock_encoder = mock.MagicMock()
        mock_encoding = mock.MagicMock()
        mock_encoder.return_value = mock_encoding
        mock_encoding.encode.return_value = '{"value": 37}'

        client = self.client_class(json_encoder=mock_encoder)
        # Vendored tree JSON content types are accepted.
        client.post(
            "/json_view/", {"value": 37}, content_type="application/vnd.api+json"
        )
        self.assertTrue(mock_encoder.called)
        self.assertTrue(mock_encoding.encode.called)

    def test_put(self):
        response = self.client.put("/put_view/", {"foo": "bar"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "PUT Template")
        self.assertEqual(response.context["data"], "{'foo': 'bar'}")
        self.assertEqual(response.context["Content-Length"], "14")

    def test_trace(self):
        """TRACE a view"""
        response = self.client.trace("/trace_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["method"], "TRACE")
        self.assertEqual(response.templates[0].name, "TRACE Template")

    def test_response_headers(self):
        "Check the value of HTTP headers returned in a response"
        response = self.client.get("/header_view/")

        self.assertEqual(response.headers["X-DJANGO-TEST"], "Slartibartfast")

    def test_response_attached_request(self):
        """
        The returned response has a ``request`` attribute with the originating
        environ dict and a ``wsgi_request`` with the originating WSGIRequest.
        """
        response = self.client.get("/header_view/")

        self.assertTrue(hasattr(response, "request"))
        self.assertTrue(hasattr(response, "wsgi_request"))
        for key, value in response.request.items():
            self.assertIn(key, response.wsgi_request.environ)
            self.assertEqual(response.wsgi_request.environ[key], value)

    def test_response_resolver_match(self):
        """
        The response contains a ResolverMatch instance.
        """
        response = self.client.get("/header_view/")
        self.assertTrue(hasattr(response, "resolver_match"))

    def test_response_resolver_match_redirect_follow(self):
        """
        The response ResolverMatch instance contains the correct
        information when following redirects.
        """
        response = self.client.get("/redirect_view/", follow=True)
        self.assertEqual(response.resolver_match.url_name, "get_view")

    def test_response_resolver_match_regular_view(self):
        """
        The response ResolverMatch instance contains the correct
        information when accessing a regular view.
        """
        response = self.client.get("/get_view/")
        self.assertEqual(response.resolver_match.url_name, "get_view")

    @modify_settings(MIDDLEWARE={"prepend": "test_client.tests.middleware_urlconf"})
    def test_response_resolver_match_middleware_urlconf(self):
        response = self.client.get("/middleware_urlconf_view/")
        self.assertEqual(response.resolver_match.url_name, "middleware_urlconf_view")

    def test_raw_post(self):
        "POST raw data (with a content type) to a view"
        test_doc = """<?xml version="1.0" encoding="utf-8"?>
        <library><book><title>Blink</title><author>Malcolm Gladwell</author></book>
        </library>
        """
        response = self.client.post(
            "/raw_post_view/", test_doc, content_type="text/xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "Book template")
        self.assertEqual(response.content, b"Blink - Malcolm Gladwell")

    def test_insecure(self):
        "GET a URL through http"
        response = self.client.get("/secure_view/", secure=False)
        self.assertFalse(response.test_was_secure_request)
        self.assertEqual(response.test_server_port, "80")

    def test_secure(self):
        "GET a URL through https"
        response = self.client.get("/secure_view/", secure=True)
        self.assertTrue(response.test_was_secure_request)
        self.assertEqual(response.test_server_port, "443")

    def test_redirect(self):
        "GET a URL that redirects elsewhere"
        response = self.client.get("/redirect_view/")
        self.assertRedirects(response, "/get_view/")

    def test_redirect_with_query(self):
        "GET a URL that redirects with given GET parameters"
        response = self.client.get("/redirect_view/", {"var": "value"})
        self.assertRedirects(response, "/get_view/?var=value")

    def test_redirect_with_query_ordering(self):
        """assertRedirects() ignores the order of query string parameters."""
        response = self.client.get("/redirect_view/", {"var": "value", "foo": "bar"})
        self.assertRedirects(response, "/get_view/?var=value&foo=bar")
        self.assertRedirects(response, "/get_view/?foo=bar&var=value")

    def test_permanent_redirect(self):
        "GET a URL that redirects permanently elsewhere"
        response = self.client.get("/permanent_redirect_view/")
        self.assertRedirects(response, "/get_view/", status_code=301)

    def test_temporary_redirect(self):
        "GET a URL that does a non-permanent redirect"
        response = self.client.get("/temporary_redirect_view/")
        self.assertRedirects(response, "/get_view/", status_code=302)

    def test_redirect_to_strange_location(self):
        "GET a URL that redirects to a non-200 page"
        response = self.client.get("/double_redirect_view/")
        # The response was a 302, and that the attempt to get the redirection
        # location returned 301 when retrieved
        self.assertRedirects(
            response, "/permanent_redirect_view/", target_status_code=301
        )

    def test_follow_redirect(self):
        "A URL that redirects can be followed to termination."
        response = self.client.get("/double_redirect_view/", follow=True)
        self.assertRedirects(
            response, "/get_view/", status_code=302, target_status_code=200
        )
        self.assertEqual(len(response.redirect_chain), 2)

    def test_follow_relative_redirect(self):
        "A URL with a relative redirect can be followed."
        response = self.client.get("/accounts/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/accounts/login/")

    def test_follow_relative_redirect_no_trailing_slash(self):
        "A URL with a relative redirect with no trailing slash can be followed."
        response = self.client.get("/accounts/no_trailing_slash", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/accounts/login/")

    def test_redirect_to_querystring_only(self):
        """A URL that consists of a querystring only can be followed"""
        response = self.client.post("/post_then_get_view/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/post_then_get_view/")
        self.assertEqual(response.content, b"The value of success is true.")

    def test_follow_307_and_308_redirect(self):
        """
        A 307 or 308 redirect preserves the request method after the redirect.
        """
        methods = ("get", "post", "head", "options", "put", "patch", "delete", "trace")
        codes = (307, 308)
        for method, code in itertools.product(methods, codes):
            with self.subTest(method=method, code=code):
                req_method = getattr(self.client, method)
                response = req_method(
                    "/redirect_view_%s/" % code, data={"value": "test"}, follow=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.request["PATH_INFO"], "/post_view/")
                self.assertEqual(response.request["REQUEST_METHOD"], method.upper())

    def test_follow_307_and_308_preserves_query_string(self):
        methods = ("post", "options", "put", "patch", "delete", "trace")
        codes = (307, 308)
        for method, code in itertools.product(methods, codes):
            with self.subTest(method=method, code=code):
                req_method = getattr(self.client, method)
                response = req_method(
                    "/redirect_view_%s_query_string/" % code,
                    data={"value": "test"},
                    follow=True,
                )
                self.assertRedirects(
                    response, "/post_view/?hello=world", status_code=code
                )
                self.assertEqual(response.request["QUERY_STRING"], "hello=world")

    def test_follow_307_and_308_get_head_query_string(self):
        methods = ("get", "head")
        codes = (307, 308)
        for method, code in itertools.product(methods, codes):
            with self.subTest(method=method, code=code):
                req_method = getattr(self.client, method)
                response = req_method(
                    "/redirect_view_%s_query_string/" % code,
                    data={"value": "test"},
                    follow=True,
                )
                self.assertRedirects(
                    response, "/post_view/?hello=world", status_code=code
                )
                self.assertEqual(response.request["QUERY_STRING"], "value=test")

    def test_follow_307_and_308_preserves_post_data(self):
        for code in (307, 308):
            with self.subTest(code=code):
                response = self.client.post(
                    "/redirect_view_%s/" % code, data={"value": "test"}, follow=True
                )
                self.assertContains(response, "test is the value")

    def test_follow_307_and_308_preserves_put_body(self):
        for code in (307, 308):
            with self.subTest(code=code):
                response = self.client.put(
                    "/redirect_view_%s/?to=/put_view/" % code, data="a=b", follow=True
                )
                self.assertContains(response, "a=b is the body")

    def test_follow_307_and_308_preserves_get_params(self):
        data = {"var": 30, "to": "/get_view/"}
        for code in (307, 308):
            with self.subTest(code=code):
                response = self.client.get(
                    "/redirect_view_%s/" % code, data=data, follow=True
                )
                self.assertContains(response, "30 is the value")

    def test_redirect_http(self):
        """GET a URL that redirects to an HTTP URI."""
        response = self.client.get("/http_redirect_view/", follow=True)
        self.assertFalse(response.test_was_secure_request)

    def test_redirect_https(self):
        """GET a URL that redirects to an HTTPS URI."""
        response = self.client.get("/https_redirect_view/", follow=True)
        self.assertTrue(response.test_was_secure_request)

    def test_notfound_response(self):
        "GET a URL that responds as '404:Not Found'"
        response = self.client.get("/bad_view/")
        self.assertContains(response, "MAGIC", status_code=404)

    def test_valid_form(self):
        "POST valid data to a form"
        post_data = {
            "text": "Hello World",
            "email": "foo@example.com",
            "value": 37,
            "single": "b",
            "multi": ("b", "c", "e"),
        }
        response = self.client.post("/form_view/", post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Valid POST Template")

    def test_valid_form_with_hints(self):
        "GET a form, providing hints in the GET data"
        hints = {"text": "Hello World", "multi": ("b", "c", "e")}
        response = self.client.get("/form_view/", data=hints)
        # The multi-value data has been rolled out ok
        self.assertContains(response, "Select a valid choice.", 0)
        self.assertTemplateUsed(response, "Form GET Template")

    def test_incomplete_data_form(self):
        "POST incomplete data to a form"
        post_data = {"text": "Hello World", "value": 37}
        response = self.client.post("/form_view/", post_data)
        self.assertContains(response, "This field is required.", 3)
        self.assertTemplateUsed(response, "Invalid POST Template")

        self.assertFormError(response, "form", "email", "This field is required.")
        self.assertFormError(response, "form", "single", "This field is required.")
        self.assertFormError(response, "form", "multi", "This field is required.")

    def test_form_error(self):
        "POST erroneous data to a form"
        post_data = {
            "text": "Hello World",
            "email": "not an email address",
            "value": 37,
            "single": "b",
            "multi": ("b", "c", "e"),
        }
        response = self.client.post("/form_view/", post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        self.assertFormError(response, "form", "email", "Enter a valid email address.")

    def test_valid_form_with_template(self):
        "POST valid data to a form using multiple templates"
        post_data = {
            "text": "Hello World",
            "email": "foo@example.com",
            "value": 37,
            "single": "b",
            "multi": ("b", "c", "e"),
        }
        response = self.client.post("/form_view_with_template/", post_data)
        self.assertContains(response, "POST data OK")
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateNotUsed(response, "Valid POST Template")

    def test_incomplete_data_form_with_template(self):
        "POST incomplete data to a form using multiple templates"
        post_data = {"text": "Hello World", "value": 37}
        response = self.client.post("/form_view_with_template/", post_data)
        self.assertContains(response, "POST data has errors")
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateNotUsed(response, "Invalid POST Template")

        self.assertFormError(response, "form", "email", "This field is required.")
        self.assertFormError(response, "form", "single", "This field is required.")
        self.assertFormError(response, "form", "multi", "This field is required.")

    def test_form_error_with_template(self):
        "POST erroneous data to a form using multiple templates"
        post_data = {
            "text": "Hello World",
            "email": "not an email address",
            "value": 37,
            "single": "b",
            "multi": ("b", "c", "e"),
        }
        response = self.client.post("/form_view_with_template/", post_data)
        self.assertContains(response, "POST data has errors")
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateNotUsed(response, "Invalid POST Template")

        self.assertFormError(response, "form", "email", "Enter a valid email address.")

    def test_unknown_page(self):
        "GET an invalid URL"
        response = self.client.get("/unknown_view/")

        # The response was a 404
        self.assertEqual(response.status_code, 404)

    def test_url_parameters(self):
        "Make sure that URL ;-parameters are not stripped."
        response = self.client.get("/unknown_view/;some-parameter")

        # The path in the response includes it (ignore that it's a 404)
        self.assertEqual(response.request["PATH_INFO"], "/unknown_view/;some-parameter")

    def test_view_with_login(self):
        "Request a page that is protected with @login_required"

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    @override_settings(
        INSTALLED_APPS=["django.contrib.auth"],
        SESSION_ENGINE="django.contrib.sessions.backends.file",
    )
    def test_view_with_login_when_sessions_app_is_not_installed(self):
        self.test_view_with_login()

    def test_view_with_force_login(self):
        "Request a page that is protected with @login_required"
        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

        # Log in
        self.client.force_login(self.u1)

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    def test_view_with_method_login(self):
        "Request a page that is protected with a @login_required method"

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_method_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/login_protected_method_view/"
        )

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Request a page that requires a login
        response = self.client.get("/login_protected_method_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    def test_view_with_method_force_login(self):
        "Request a page that is protected with a @login_required method"
        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_method_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/login_protected_method_view/"
        )

        # Log in
        self.client.force_login(self.u1)

        # Request a page that requires a login
        response = self.client.get("/login_protected_method_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    def test_view_with_login_and_custom_redirect(self):
        """
        Request a page that is protected with
        @login_required(redirect_field_name='redirect_to')
        """

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view_custom_redirect/")
        self.assertRedirects(
            response,
            "/accounts/login/?redirect_to=/login_protected_view_custom_redirect/",
        )

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Request a page that requires a login
        response = self.client.get("/login_protected_view_custom_redirect/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    def test_view_with_force_login_and_custom_redirect(self):
        """
        Request a page that is protected with
        @login_required(redirect_field_name='redirect_to')
        """
        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view_custom_redirect/")
        self.assertRedirects(
            response,
            "/accounts/login/?redirect_to=/login_protected_view_custom_redirect/",
        )

        # Log in
        self.client.force_login(self.u1)

        # Request a page that requires a login
        response = self.client.get("/login_protected_view_custom_redirect/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    def test_view_with_bad_login(self):
        "Request a page that is protected with @login, but use bad credentials"

        login = self.client.login(username="otheruser", password="nopassword")
        self.assertFalse(login)

    def test_view_with_inactive_login(self):
        """
        An inactive user may login if the authenticate backend allows it.
        """
        credentials = {"username": "inactive", "password": "password"}
        self.assertFalse(self.client.login(**credentials))

        with self.settings(
            AUTHENTICATION_BACKENDS=[
                "django.contrib.auth.backends.AllowAllUsersModelBackend"
            ]
        ):
            self.assertTrue(self.client.login(**credentials))

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_view_with_inactive_force_login(self):
        "Request a page that is protected with @login, but use an inactive login"

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

        # Log in
        self.client.force_login(
            self.u2, backend="django.contrib.auth.backends.AllowAllUsersModelBackend"
        )

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "inactive")

    def test_logout(self):
        "Request a logout after logging in"
        # Log in
        self.client.login(username="testclient", password="password")

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

        # Log out
        self.client.logout()

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

    def test_logout_with_force_login(self):
        "Request a logout after logging in"
        # Log in
        self.client.force_login(self.u1)

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

        # Log out
        self.client.logout()

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "test_client.auth_backends.TestClientBackend",
        ],
    )
    def test_force_login_with_backend(self):
        """
        Request a page that is protected with @login_required when using
        force_login() and passing a backend.
        """
        # Get the page without logging in. Should result in 302.
        response = self.client.get("/login_protected_view/")
        self.assertRedirects(response, "/accounts/login/?next=/login_protected_view/")

        # Log in
        self.client.force_login(
            self.u1, backend="test_client.auth_backends.TestClientBackend"
        )
        self.assertEqual(self.u1.backend, "test_client.auth_backends.TestClientBackend")

        # Request a page that requires a login
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "test_client.auth_backends.TestClientBackend",
        ],
    )
    def test_force_login_without_backend(self):
        """
        force_login() without passing a backend and with multiple backends
        configured should automatically use the first backend.
        """
        self.client.force_login(self.u1)
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")
        self.assertEqual(self.u1.backend, "django.contrib.auth.backends.ModelBackend")

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "test_client.auth_backends.BackendWithoutGetUserMethod",
            "django.contrib.auth.backends.ModelBackend",
        ]
    )
    def test_force_login_with_backend_missing_get_user(self):
        """
        force_login() skips auth backends without a get_user() method.
        """
        self.client.force_login(self.u1)
        self.assertEqual(self.u1.backend, "django.contrib.auth.backends.ModelBackend")

    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
    def test_logout_cookie_sessions(self):
        self.test_logout()

    def test_view_with_permissions(self):
        "Request a page that is protected with @permission_required"

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/permission_protected_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/permission_protected_view/"
        )

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Log in with wrong permissions. Should result in 302.
        response = self.client.get("/permission_protected_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/permission_protected_view/"
        )

        # TODO: Log in with right permissions and request the page again

    def test_view_with_permissions_exception(self):
        """
        Request a page that is protected with @permission_required but raises
        an exception.
        """

        # Get the page without logging in. Should result in 403.
        response = self.client.get("/permission_protected_view_exception/")
        self.assertEqual(response.status_code, 403)

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Log in with wrong permissions. Should result in 403.
        response = self.client.get("/permission_protected_view_exception/")
        self.assertEqual(response.status_code, 403)

    def test_view_with_method_permissions(self):
        "Request a page that is protected with a @permission_required method"

        # Get the page without logging in. Should result in 302.
        response = self.client.get("/permission_protected_method_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/permission_protected_method_view/"
        )

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Log in with wrong permissions. Should result in 302.
        response = self.client.get("/permission_protected_method_view/")
        self.assertRedirects(
            response, "/accounts/login/?next=/permission_protected_method_view/"
        )

        # TODO: Log in with right permissions and request the page again

    def test_external_redirect(self):
        response = self.client.get("/django_project_redirect/")
        self.assertRedirects(
            response, "https://www.djangoproject.com/", fetch_redirect_response=False
        )

    def test_external_redirect_without_trailing_slash(self):
        """
        Client._handle_redirects() with an empty path.
        """
        response = self.client.get("/no_trailing_slash_external_redirect/", follow=True)
        self.assertRedirects(response, "https://testserver")

    def test_external_redirect_with_fetch_error_msg(self):
        """
        assertRedirects without fetch_redirect_response=False raises
        a relevant ValueError rather than a non-descript AssertionError.
        """
        response = self.client.get("/django_project_redirect/")
        msg = (
            "The test client is unable to fetch remote URLs (got "
            "https://www.djangoproject.com/). If the host is served by Django, "
            "add 'www.djangoproject.com' to ALLOWED_HOSTS. "
            "Otherwise, use assertRedirects(..., fetch_redirect_response=False)."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.assertRedirects(response, "https://www.djangoproject.com/")

    def test_session_modifying_view(self):
        "Request a page that modifies the session"
        # Session value isn't set initially
        with self.assertRaises(KeyError):
            self.client.session["tobacconist"]

        self.client.post("/session_view/")
        # The session was modified
        self.assertEqual(self.client.session["tobacconist"], "hovercraft")

    @override_settings(
        INSTALLED_APPS=[],
        SESSION_ENGINE="django.contrib.sessions.backends.file",
    )
    def test_sessions_app_is_not_installed(self):
        self.test_session_modifying_view()

    @override_settings(
        INSTALLED_APPS=[],
        SESSION_ENGINE="django.contrib.sessions.backends.nonexistent",
    )
    def test_session_engine_is_invalid(self):
        with self.assertRaisesMessage(ImportError, "nonexistent"):
            self.test_session_modifying_view()

    def test_view_with_exception(self):
        "Request a page that is known to throw an error"
        with self.assertRaises(KeyError):
            self.client.get("/broken_view/")

    def test_exc_info(self):
        client = Client(raise_request_exception=False)
        response = client.get("/broken_view/")
        self.assertEqual(response.status_code, 500)
        exc_type, exc_value, exc_traceback = response.exc_info
        self.assertIs(exc_type, KeyError)
        self.assertIsInstance(exc_value, KeyError)
        self.assertEqual(str(exc_value), "'Oops! Looks like you wrote some bad code.'")
        self.assertIsNotNone(exc_traceback)

    def test_exc_info_none(self):
        response = self.client.get("/get_view/")
        self.assertIsNone(response.exc_info)

    def test_mail_sending(self):
        "Mail is redirected to a dummy outbox during test setup"
        response = self.client.get("/mail_sending_view/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test message")
        self.assertEqual(mail.outbox[0].body, "This is a test email")
        self.assertEqual(mail.outbox[0].from_email, "from@example.com")
        self.assertEqual(mail.outbox[0].to[0], "first@example.com")
        self.assertEqual(mail.outbox[0].to[1], "second@example.com")

    def test_reverse_lazy_decodes(self):
        "reverse_lazy() works in the test client"
        data = {"var": "data"}
        response = self.client.get(reverse_lazy("get_view"), data)

        # Check some response details
        self.assertContains(response, "This is a test")

    def test_relative_redirect(self):
        response = self.client.get("/accounts/")
        self.assertRedirects(response, "/accounts/login/")

    def test_relative_redirect_no_trailing_slash(self):
        response = self.client.get("/accounts/no_trailing_slash")
        self.assertRedirects(response, "/accounts/login/")

    def test_mass_mail_sending(self):
        "Mass mail is redirected to a dummy outbox during test setup"
        response = self.client.get("/mass_mail_sending_view/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, "First Test message")
        self.assertEqual(mail.outbox[0].body, "This is the first test email")
        self.assertEqual(mail.outbox[0].from_email, "from@example.com")
        self.assertEqual(mail.outbox[0].to[0], "first@example.com")
        self.assertEqual(mail.outbox[0].to[1], "second@example.com")

        self.assertEqual(mail.outbox[1].subject, "Second Test message")
        self.assertEqual(mail.outbox[1].body, "This is the second test email")
        self.assertEqual(mail.outbox[1].from_email, "from@example.com")
        self.assertEqual(mail.outbox[1].to[0], "second@example.com")
        self.assertEqual(mail.outbox[1].to[1], "third@example.com")

    def test_exception_following_nested_client_request(self):
        """
        A nested test client request shouldn't clobber exception signals from
        the outer client request.
        """
        with self.assertRaisesMessage(Exception, "exception message"):
            self.client.get("/nesting_exception_view/")

    def test_response_raises_multi_arg_exception(self):
        """A request may raise an exception with more than one required arg."""
        with self.assertRaises(TwoArgException) as cm:
            self.client.get("/two_arg_exception/")
        self.assertEqual(cm.exception.args, ("one", "two"))

    def test_uploading_temp_file(self):
        with tempfile.TemporaryFile() as test_file:
            response = self.client.post("/upload_view/", data={"temp_file": test_file})
        self.assertEqual(response.content, b"temp_file")

    def test_uploading_named_temp_file(self):
        with tempfile.NamedTemporaryFile() as test_file:
            response = self.client.post(
                "/upload_view/",
                data={"named_temp_file": test_file},
            )
        self.assertEqual(response.content, b"named_temp_file")


@override_settings(
    MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
    ROOT_URLCONF="test_client.urls",
)
class CSRFEnabledClientTests(SimpleTestCase):
    def test_csrf_enabled_client(self):
        "A client can be instantiated with CSRF checks enabled"
        csrf_client = Client(enforce_csrf_checks=True)
        # The normal client allows the post
        response = self.client.post("/post_view/", {})
        self.assertEqual(response.status_code, 200)
        # The CSRF-enabled client rejects it
        response = csrf_client.post("/post_view/", {})
        self.assertEqual(response.status_code, 403)


class CustomTestClient(Client):
    i_am_customized = "Yes"


class CustomTestClientTest(SimpleTestCase):
    client_class = CustomTestClient

    def test_custom_test_client(self):
        """A test case can specify a custom class for self.client."""
        self.assertIs(hasattr(self.client, "i_am_customized"), True)


def _generic_view(request):
    return HttpResponse(status=200)


@override_settings(ROOT_URLCONF="test_client.urls")
class RequestFactoryTest(SimpleTestCase):
    """Tests for the request factory."""

    # A mapping between names of HTTP/1.1 methods and their test views.
    http_methods_and_views = (
        ("get", get_view),
        ("post", post_view),
        ("put", _generic_view),
        ("patch", _generic_view),
        ("delete", _generic_view),
        ("head", _generic_view),
        ("options", _generic_view),
        ("trace", trace_view),
    )
    request_factory = RequestFactory()

    def test_request_factory(self):
        """The request factory implements all the HTTP/1.1 methods."""
        for method_name, view in self.http_methods_and_views:
            method = getattr(self.request_factory, method_name)
            request = method("/somewhere/")
            response = view(request)
            self.assertEqual(response.status_code, 200)

    def test_get_request_from_factory(self):
        """
        The request factory returns a templated response for a GET request.
        """
        request = self.request_factory.get("/somewhere/")
        response = get_view(request)
        self.assertContains(response, "This is a test")

    def test_trace_request_from_factory(self):
        """The request factory returns an echo response for a TRACE request."""
        url_path = "/somewhere/"
        request = self.request_factory.trace(url_path)
        response = trace_view(request)
        protocol = request.META["SERVER_PROTOCOL"]
        echoed_request_line = "TRACE {} {}".format(url_path, protocol)
        self.assertContains(response, echoed_request_line)


@override_settings(ROOT_URLCONF="test_client.urls")
class AsyncClientTest(TestCase):
    async def test_response_resolver_match(self):
        response = await self.async_client.get("/async_get_view/")
        self.assertTrue(hasattr(response, "resolver_match"))
        self.assertEqual(response.resolver_match.url_name, "async_get_view")

    @modify_settings(
        MIDDLEWARE={"prepend": "test_client.tests.async_middleware_urlconf"},
    )
    async def test_response_resolver_match_middleware_urlconf(self):
        response = await self.async_client.get("/middleware_urlconf_view/")
        self.assertEqual(response.resolver_match.url_name, "middleware_urlconf_view")

    async def test_follow_parameter_not_implemented(self):
        msg = "AsyncClient request methods do not accept the follow parameter."
        tests = (
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "options",
            "trace",
        )
        for method_name in tests:
            with self.subTest(method=method_name):
                method = getattr(self.async_client, method_name)
                with self.assertRaisesMessage(NotImplementedError, msg):
                    await method("/redirect_view/", follow=True)

    async def test_get_data(self):
        response = await self.async_client.get("/get_view/", {"var": "val"})
        self.assertContains(response, "This is a test. val is the value.")


@override_settings(ROOT_URLCONF="test_client.urls")
class AsyncRequestFactoryTest(SimpleTestCase):
    request_factory = AsyncRequestFactory()

    async def test_request_factory(self):
        tests = (
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "options",
            "trace",
        )
        for method_name in tests:
            with self.subTest(method=method_name):

                async def async_generic_view(request):
                    if request.method.lower() != method_name:
                        return HttpResponseNotAllowed(method_name)
                    return HttpResponse(status=200)

                method = getattr(self.request_factory, method_name)
                request = method("/somewhere/")
                response = await async_generic_view(request)
                self.assertEqual(response.status_code, 200)

    async def test_request_factory_data(self):
        async def async_generic_view(request):
            return HttpResponse(status=200, content=request.body)

        request = self.request_factory.post(
            "/somewhere/",
            data={"example": "data"},
            content_type="application/json",
        )
        self.assertEqual(request.headers["content-length"], "19")
        self.assertEqual(request.headers["content-type"], "application/json")
        response = await async_generic_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"example": "data"}')

    def test_request_factory_sets_headers(self):
        request = self.request_factory.get(
            "/somewhere/",
            AUTHORIZATION="Bearer faketoken",
            X_ANOTHER_HEADER="some other value",
        )
        self.assertEqual(request.headers["authorization"], "Bearer faketoken")
        self.assertIn("HTTP_AUTHORIZATION", request.META)
        self.assertEqual(request.headers["x-another-header"], "some other value")
        self.assertIn("HTTP_X_ANOTHER_HEADER", request.META)

    def test_request_factory_query_string(self):
        request = self.request_factory.get("/somewhere/", {"example": "data"})
        self.assertNotIn("Query-String", request.headers)
        self.assertEqual(request.GET["example"], "data")
