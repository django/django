from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIHandler, WSGIRequest, get_script_name
from django.core.signals import request_finished, request_started
from django.db import close_old_connections, connection
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TransactionTestCase,
    override_settings,
)


class HandlerTests(SimpleTestCase):
    request_factory = RequestFactory()

    def setUp(self):
        request_started.disconnect(close_old_connections)

    def tearDown(self):
        request_started.connect(close_old_connections)

    def test_middleware_initialized(self):
        handler = WSGIHandler()
        self.assertIsNotNone(handler._middleware_chain)

    def test_bad_path_info(self):
        """
        A non-UTF-8 path populates PATH_INFO with an URL-encoded path and
        produces a 404.
        """
        environ = self.request_factory.get("/").environ
        environ["PATH_INFO"] = "\xed"
        handler = WSGIHandler()
        response = handler(environ, lambda *a, **k: None)
        # The path of the request will be encoded to '/%ED'.
        self.assertEqual(response.status_code, 404)

    def test_non_ascii_query_string(self):
        """
        Non-ASCII query strings are properly decoded (#20530, #22996).
        """
        environ = self.request_factory.get("/").environ
        raw_query_strings = [
            b"want=caf%C3%A9",  # This is the proper way to encode 'café'
            b"want=caf\xc3\xa9",  # UA forgot to quote bytes
            b"want=caf%E9",  # UA quoted, but not in UTF-8
            # UA forgot to convert Latin-1 to UTF-8 and to quote (typical of
            # MSIE).
            b"want=caf\xe9",
        ]
        got = []
        for raw_query_string in raw_query_strings:
            # Simulate http.server.BaseHTTPRequestHandler.parse_request
            # handling of raw request.
            environ["QUERY_STRING"] = str(raw_query_string, "iso-8859-1")
            request = WSGIRequest(environ)
            got.append(request.GET["want"])
        # %E9 is converted to the Unicode replacement character by parse_qsl
        self.assertEqual(got, ["café", "café", "caf\ufffd", "café"])

    def test_non_ascii_cookie(self):
        """Non-ASCII cookies set in JavaScript are properly decoded (#20557)."""
        environ = self.request_factory.get("/").environ
        raw_cookie = 'want="café"'.encode("utf-8").decode("iso-8859-1")
        environ["HTTP_COOKIE"] = raw_cookie
        request = WSGIRequest(environ)
        self.assertEqual(request.COOKIES["want"], "café")

    def test_invalid_unicode_cookie(self):
        """
        Invalid cookie content should result in an absent cookie, but not in a
        crash while trying to decode it (#23638).
        """
        environ = self.request_factory.get("/").environ
        environ["HTTP_COOKIE"] = "x=W\x03c(h]\x8e"
        request = WSGIRequest(environ)
        # We don't test COOKIES content, as the result might differ between
        # Python version because parsing invalid content became stricter in
        # latest versions.
        self.assertIsInstance(request.COOKIES, dict)

    @override_settings(ROOT_URLCONF="handlers.urls")
    def test_invalid_multipart_boundary(self):
        """
        Invalid boundary string should produce a "Bad Request" response, not a
        server error (#23887).
        """
        environ = self.request_factory.post("/malformed_post/").environ
        environ["CONTENT_TYPE"] = "multipart/form-data; boundary=WRONG\x07"
        handler = WSGIHandler()
        response = handler(environ, lambda *a, **k: None)
        # Expect "bad request" response
        self.assertEqual(response.status_code, 400)


@override_settings(ROOT_URLCONF="handlers.urls", MIDDLEWARE=[])
class TransactionsPerRequestTests(TransactionTestCase):
    available_apps = []

    def test_no_transaction(self):
        response = self.client.get("/in_transaction/")
        self.assertContains(response, "False")

    def test_auto_transaction(self):
        old_atomic_requests = connection.settings_dict["ATOMIC_REQUESTS"]
        try:
            connection.settings_dict["ATOMIC_REQUESTS"] = True
            response = self.client.get("/in_transaction/")
        finally:
            connection.settings_dict["ATOMIC_REQUESTS"] = old_atomic_requests
        self.assertContains(response, "True")

    async def test_auto_transaction_async_view(self):
        old_atomic_requests = connection.settings_dict["ATOMIC_REQUESTS"]
        try:
            connection.settings_dict["ATOMIC_REQUESTS"] = True
            msg = "You cannot use ATOMIC_REQUESTS with async views."
            with self.assertRaisesMessage(RuntimeError, msg):
                await self.async_client.get("/async_regular/")
        finally:
            connection.settings_dict["ATOMIC_REQUESTS"] = old_atomic_requests

    def test_no_auto_transaction(self):
        old_atomic_requests = connection.settings_dict["ATOMIC_REQUESTS"]
        try:
            connection.settings_dict["ATOMIC_REQUESTS"] = True
            response = self.client.get("/not_in_transaction/")
        finally:
            connection.settings_dict["ATOMIC_REQUESTS"] = old_atomic_requests
        self.assertContains(response, "False")


@override_settings(ROOT_URLCONF="handlers.urls")
class SignalsTests(SimpleTestCase):
    def setUp(self):
        self.signals = []
        self.signaled_environ = None
        request_started.connect(self.register_started)
        request_finished.connect(self.register_finished)

    def tearDown(self):
        request_started.disconnect(self.register_started)
        request_finished.disconnect(self.register_finished)

    def register_started(self, **kwargs):
        self.signals.append("started")
        self.signaled_environ = kwargs.get("environ")

    def register_finished(self, **kwargs):
        self.signals.append("finished")

    def test_request_signals(self):
        response = self.client.get("/regular/")
        self.assertEqual(self.signals, ["started", "finished"])
        self.assertEqual(response.content, b"regular content")
        self.assertEqual(self.signaled_environ, response.wsgi_request.environ)

    def test_request_signals_streaming_response(self):
        response = self.client.get("/streaming/")
        self.assertEqual(self.signals, ["started"])
        self.assertEqual(b"".join(response.streaming_content), b"streaming content")
        self.assertEqual(self.signals, ["started", "finished"])


def empty_middleware(get_response):
    pass


@override_settings(ROOT_URLCONF="handlers.urls")
class HandlerRequestTests(SimpleTestCase):
    request_factory = RequestFactory()

    def test_async_view(self):
        """Calling an async view down the normal synchronous path."""
        response = self.client.get("/async_regular/")
        self.assertEqual(response.status_code, 200)

    def test_suspiciousop_in_view_returns_400(self):
        response = self.client.get("/suspicious/")
        self.assertEqual(response.status_code, 400)

    def test_bad_request_in_view_returns_400(self):
        response = self.client.get("/bad_request/")
        self.assertEqual(response.status_code, 400)

    def test_invalid_urls(self):
        response = self.client.get("~%A9helloworld")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.context["request_path"], "/~%25A9helloworld")

        response = self.client.get("d%aao%aaw%aan%aal%aao%aaa%aad%aa/")
        self.assertEqual(
            response.context["request_path"],
            "/d%25AAo%25AAw%25AAn%25AAl%25AAo%25AAa%25AAd%25AA",
        )

        response = self.client.get("/%E2%99%E2%99%A5/")
        self.assertEqual(response.context["request_path"], "/%25E2%2599%E2%99%A5/")

        response = self.client.get("/%E2%98%8E%E2%A9%E2%99%A5/")
        self.assertEqual(
            response.context["request_path"], "/%E2%98%8E%25E2%25A9%E2%99%A5/"
        )

    def test_environ_path_info_type(self):
        environ = self.request_factory.get("/%E2%A8%87%87%A5%E2%A8%A0").environ
        self.assertIsInstance(environ["PATH_INFO"], str)

    def test_handle_accepts_httpstatus_enum_value(self):
        def start_response(status, headers):
            start_response.status = status

        environ = self.request_factory.get("/httpstatus_enum/").environ
        WSGIHandler()(environ, start_response)
        self.assertEqual(start_response.status, "200 OK")

    @override_settings(MIDDLEWARE=["handlers.tests.empty_middleware"])
    def test_middleware_returns_none(self):
        msg = "Middleware factory handlers.tests.empty_middleware returned None."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.client.get("/")

    def test_no_response(self):
        msg = (
            "The view %s didn't return an HttpResponse object. It returned None "
            "instead."
        )
        tests = (
            ("/no_response_fbv/", "handlers.views.no_response"),
            ("/no_response_cbv/", "handlers.views.NoResponse.__call__"),
        )
        for url, view in tests:
            with self.subTest(url=url), self.assertRaisesMessage(
                ValueError, msg % view
            ):
                self.client.get(url)


class ScriptNameTests(SimpleTestCase):
    def test_get_script_name(self):
        # Regression test for #23173
        # Test first without PATH_INFO
        script_name = get_script_name({"SCRIPT_URL": "/foobar/"})
        self.assertEqual(script_name, "/foobar/")

        script_name = get_script_name({"SCRIPT_URL": "/foobar/", "PATH_INFO": "/"})
        self.assertEqual(script_name, "/foobar")

    def test_get_script_name_double_slashes(self):
        """
        WSGI squashes multiple successive slashes in PATH_INFO, get_script_name
        should take that into account when forming SCRIPT_NAME (#17133).
        """
        script_name = get_script_name(
            {
                "SCRIPT_URL": "/mst/milestones//accounts/login//help",
                "PATH_INFO": "/milestones/accounts/login/help",
            }
        )
        self.assertEqual(script_name, "/mst")


@override_settings(ROOT_URLCONF="handlers.urls")
class AsyncHandlerRequestTests(SimpleTestCase):
    """Async variants of the normal handler request tests."""

    async def test_sync_view(self):
        """Calling a sync view down the asynchronous path."""
        response = await self.async_client.get("/regular/")
        self.assertEqual(response.status_code, 200)

    async def test_async_view(self):
        """Calling an async view down the asynchronous path."""
        response = await self.async_client.get("/async_regular/")
        self.assertEqual(response.status_code, 200)

    async def test_suspiciousop_in_view_returns_400(self):
        response = await self.async_client.get("/suspicious/")
        self.assertEqual(response.status_code, 400)

    async def test_bad_request_in_view_returns_400(self):
        response = await self.async_client.get("/bad_request/")
        self.assertEqual(response.status_code, 400)

    async def test_no_response(self):
        msg = (
            "The view handlers.views.no_response didn't return an "
            "HttpResponse object. It returned None instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            await self.async_client.get("/no_response_fbv/")

    async def test_unawaited_response(self):
        msg = (
            "The view handlers.views.CoroutineClearingView.__call__ didn't"
            " return an HttpResponse object. It returned an unawaited"
            " coroutine instead. You may need to add an 'await'"
            " into your view."
        )
        with self.assertRaisesMessage(ValueError, msg):
            await self.async_client.get("/unawaited/")
