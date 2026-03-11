import asyncio
import sys
import threading
from io import BytesIO
from pathlib import Path

from asgiref.testing import ApplicationCommunicator

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import ASGIHandler, get_asgi_application
from django.core.exceptions import RequestDataTooBig
from django.core.handlers.asgi import ASGIRequest
from django.core.signals import request_finished, request_started
from django.db import close_old_connections
from django.test import (
    AsyncRequestFactory,
    SimpleTestCase,
    ignore_warnings,
    modify_settings,
    override_settings,
)
from django.utils.http import http_date

from .urls import sync_waiter, test_filename

TEST_STATIC_ROOT = Path(__file__).parent / "project" / "static"
TOO_MUCH_DATA_MSG = "Request body exceeded settings.DATA_UPLOAD_MAX_MEMORY_SIZE."


@override_settings(ROOT_URLCONF="asgi.urls")
class ASGITest(SimpleTestCase):
    async_request_factory = AsyncRequestFactory()

    def setUp(self):
        request_started.disconnect(close_old_connections)

    def tearDown(self):
        request_started.connect(close_old_connections)

    async def test_get_asgi_application(self):
        """
        get_asgi_application() returns a functioning ASGI callable.
        """
        application = get_asgi_application()
        # Construct HTTP request.
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        self.assertEqual(
            set(response_start["headers"]),
            {
                (b"Content-Length", b"12"),
                (b"Content-Type", b"text/html; charset=utf-8"),
            },
        )
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"Hello World!")
        # Allow response.close() to finish.
        await communicator.wait()

    # Python's file API is not async compatible. A third-party library such
    # as https://github.com/Tinche/aiofiles allows passing the file to
    # FileResponse as an async interator. With a sync iterator
    # StreamingHTTPResponse triggers a warning when iterating the file.
    # assertWarnsMessage is not async compatible, so ignore_warnings for the
    # test.
    @ignore_warnings(module="django.http.response")
    async def test_file_response(self):
        """
        Makes sure that FileResponse works over ASGI.
        """
        application = get_asgi_application()
        # Construct HTTP request.
        scope = self.async_request_factory._base_scope(path="/file/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        # Get the file content.
        with open(test_filename, "rb") as test_file:
            test_file_contents = test_file.read()
        # Read the response.
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        headers = response_start["headers"]
        self.assertEqual(len(headers), 3)
        expected_headers = {
            b"Content-Length": str(len(test_file_contents)).encode("ascii"),
            b"Content-Type": b"text/x-python",
            b"Content-Disposition": b'inline; filename="urls.py"',
        }
        for key, value in headers:
            try:
                self.assertEqual(value, expected_headers[key])
            except AssertionError:
                # Windows registry may not be configured with correct
                # mimetypes.
                if sys.platform == "win32" and key == b"Content-Type":
                    self.assertEqual(value, b"text/plain")
                else:
                    raise

        # Warning ignored here.
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], test_file_contents)
        # Allow response.close() to finish.
        await communicator.wait()

    @modify_settings(INSTALLED_APPS={"append": "django.contrib.staticfiles"})
    @override_settings(
        STATIC_URL="static/",
        STATIC_ROOT=TEST_STATIC_ROOT,
        STATICFILES_DIRS=[TEST_STATIC_ROOT],
        STATICFILES_FINDERS=[
            "django.contrib.staticfiles.finders.FileSystemFinder",
        ],
    )
    async def test_static_file_response(self):
        application = ASGIStaticFilesHandler(get_asgi_application())
        # Construct HTTP request.
        scope = self.async_request_factory._base_scope(path="/static/file.txt")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        # Get the file content.
        file_path = TEST_STATIC_ROOT / "file.txt"
        with open(file_path, "rb") as test_file:
            test_file_contents = test_file.read()
        # Read the response.
        stat = file_path.stat()
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        self.assertEqual(
            set(response_start["headers"]),
            {
                (b"Content-Length", str(len(test_file_contents)).encode("ascii")),
                (b"Content-Type", b"text/plain"),
                (b"Content-Disposition", b'inline; filename="file.txt"'),
                (b"Last-Modified", http_date(stat.st_mtime).encode("ascii")),
            },
        )
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], test_file_contents)
        # Allow response.close() to finish.
        await communicator.wait()

    async def test_headers(self):
        application = get_asgi_application()
        communicator = ApplicationCommunicator(
            application,
            self.async_request_factory._base_scope(
                path="/meta/",
                headers=[
                    [b"content-type", b"text/plain; charset=utf-8"],
                    [b"content-length", b"77"],
                    [b"referer", b"Scotland"],
                    [b"referer", b"Wales"],
                ],
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        self.assertEqual(
            set(response_start["headers"]),
            {
                (b"Content-Length", b"19"),
                (b"Content-Type", b"text/plain; charset=utf-8"),
            },
        )
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"From Scotland,Wales")
        # Allow response.close() to finish
        await communicator.wait()

    async def test_post_body(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(
            method="POST",
            path="/post/",
            query_string="echo=1",
        )
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request", "body": b"Echo!"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"Echo!")

    async def test_meta_not_modified_with_repeat_headers(self):
        scope = self.async_request_factory._base_scope(path="/", http_version="2.0")
        scope["headers"] = [(b"foo", b"bar")] * 200_000

        setitem_count = 0

        class InstrumentedDict(dict):
            def __setitem__(self, *args, **kwargs):
                nonlocal setitem_count
                setitem_count += 1
                super().__setitem__(*args, **kwargs)

        class InstrumentedASGIRequest(ASGIRequest):
            @property
            def META(self):
                return self._meta

            @META.setter
            def META(self, value):
                self._meta = InstrumentedDict(**value)

        request = InstrumentedASGIRequest(scope, None)

        self.assertEqual(len(request.headers["foo"].split(",")), 200_000)
        self.assertLessEqual(setitem_count, 100)

    async def test_underscores_in_headers_ignored(self):
        scope = self.async_request_factory._base_scope(path="/", http_version="2.0")
        scope["headers"] = [(b"some_header", b"1")]
        request = ASGIRequest(scope, None)
        # No form of the header exists anywhere.
        self.assertNotIn("Some_Header", request.headers)
        self.assertNotIn("Some-Header", request.headers)
        self.assertNotIn("SOME_HEADER", request.META)
        self.assertNotIn("SOME-HEADER", request.META)
        self.assertNotIn("HTTP_SOME_HEADER", request.META)

    async def test_untouched_request_body_gets_closed(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(method="POST", path="/post/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 204)
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"")
        # Allow response.close() to finish
        await communicator.wait()

    async def test_get_query_string(self):
        application = get_asgi_application()
        for query_string in (b"name=Andrew", "name=Andrew"):
            with self.subTest(query_string=query_string):
                scope = self.async_request_factory._base_scope(
                    path="/",
                    query_string=query_string,
                )
                communicator = ApplicationCommunicator(application, scope)
                await communicator.send_input({"type": "http.request"})
                response_start = await communicator.receive_output()
                self.assertEqual(response_start["type"], "http.response.start")
                self.assertEqual(response_start["status"], 200)
                response_body = await communicator.receive_output()
                self.assertEqual(response_body["type"], "http.response.body")
                self.assertEqual(response_body["body"], b"Hello Andrew!")
                # Allow response.close() to finish
                await communicator.wait()

    async def test_disconnect(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.disconnect"})
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output()

    async def test_wrong_connection_type(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/", type="other")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        msg = "Django can only handle ASGI/HTTP connections, not other."
        with self.assertRaisesMessage(ValueError, msg):
            await communicator.receive_output()

    async def test_non_unicode_query_string(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/", query_string=b"\xff")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 400)
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"")

    async def test_request_lifecycle_signals_dispatched_with_thread_sensitive(self):
        class SignalHandler:
            """Track threads handler is dispatched on."""

            threads = []

            def __call__(self, **kwargs):
                self.threads.append(threading.current_thread())

        signal_handler = SignalHandler()
        request_started.connect(signal_handler)
        request_finished.connect(signal_handler)

        # Perform a basic request.
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"Hello World!")
        # Give response.close() time to finish.
        await communicator.wait()

        # AsyncToSync should have executed the signals in the same thread.
        request_started_thread, request_finished_thread = signal_handler.threads
        self.assertEqual(request_started_thread, request_finished_thread)
        request_started.disconnect(signal_handler)
        request_finished.disconnect(signal_handler)

    async def test_concurrent_async_uses_multiple_thread_pools(self):
        sync_waiter.active_threads.clear()

        # Send 2 requests concurrently
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/wait/")
        communicators = []
        for _ in range(2):
            communicators.append(ApplicationCommunicator(application, scope))
            await communicators[-1].send_input({"type": "http.request"})

        # Each request must complete with a status code of 200
        # If requests aren't scheduled concurrently, the barrier in the
        # sync_wait view will time out, resulting in a 500 status code.
        for communicator in communicators:
            response_start = await communicator.receive_output()
            self.assertEqual(response_start["type"], "http.response.start")
            self.assertEqual(response_start["status"], 200)
            response_body = await communicator.receive_output()
            self.assertEqual(response_body["type"], "http.response.body")
            self.assertEqual(response_body["body"], b"Hello World!")
            # Give response.close() time to finish.
            await communicator.wait()

        # The requests should have scheduled on different threads. Note
        # active_threads is a set (a thread can only appear once), therefore
        # length is a sufficient check.
        self.assertEqual(len(sync_waiter.active_threads), 2)

        sync_waiter.active_threads.clear()


class DataUploadMaxMemorySizeASGITests(SimpleTestCase):
    def make_request(
        self,
        body,
        content_type=b"application/octet-stream",
        content_length=None,
        stream=None,
    ):
        scope = AsyncRequestFactory()._base_scope(method="POST", path="/")
        scope["headers"] = [(b"content-type", content_type)]
        if content_length is not None:
            scope["headers"].append((b"content-length", str(content_length).encode()))
        return ASGIRequest(scope, stream if stream is not None else BytesIO(body))

    def test_body_size_not_exceeded_without_content_length(self):
        body = b"x" * 5
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=5):
            self.assertEqual(self.make_request(body).body, body)

    def test_body_size_exceeded_without_content_length(self):
        request = self.make_request(b"x" * 10)
        with self.assertRaisesMessage(RequestDataTooBig, TOO_MUCH_DATA_MSG):
            with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=5):
                request.body

    def test_body_size_check_fires_before_read(self):
        # The seekable size check rejects oversized bodies before reading
        # them into memory (i.e. before calling self.read()).
        class TrackingBytesIO(BytesIO):
            calls = []

            def read(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return super().read(*args, **kwargs)

        stream = TrackingBytesIO(b"x" * 10)
        request = self.make_request(b"x" * 10, stream=stream)
        with self.assertRaisesMessage(RequestDataTooBig, TOO_MUCH_DATA_MSG):
            with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=5):
                request.body

        self.assertEqual(stream.calls, [])

    def test_post_size_exceeded_without_content_length(self):
        request = self.make_request(
            b"a=" + b"x" * 10,
            content_type=b"application/x-www-form-urlencoded",
        )
        with self.assertRaisesMessage(RequestDataTooBig, TOO_MUCH_DATA_MSG):
            with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=5):
                request.POST

    def test_no_limit(self):
        body = b"x" * 100
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=None):
            self.assertEqual(self.make_request(body).body, body)

    async def test_read_body_no_limit(self):
        chunks = [
            {"type": "http.request", "body": b"x" * 100, "more_body": True},
            {"type": "http.request", "body": b"x" * 100, "more_body": False},
        ]

        async def receive():
            return chunks.pop(0)

        handler = ASGIHandler()
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=None):
            body_file = await handler.read_body(receive)
            self.addCleanup(body_file.close)

        body_file.seek(0)
        self.assertEqual(body_file.read(), b"x" * 200)

    def test_non_multipart_body_size_enforced(self):
        # DATA_UPLOAD_MAX_MEMORY_SIZE is enforced on non-multipart bodies.
        request = self.make_request(b"x" * 100)
        with self.assertRaisesMessage(RequestDataTooBig, TOO_MUCH_DATA_MSG):
            with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=10):
                request.body

    def test_multipart_file_upload_not_limited_by_data_upload_max(self):
        # DATA_UPLOAD_MAX_MEMORY_SIZE applies to non-file fields only; a file
        # upload whose total body exceeds the limit must still succeed.
        boundary = "testboundary"
        file_content = b"x" * 100
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
                f"Content-Type: application/octet-stream\r\n"
                f"\r\n"
            ).encode()
            + file_content
            + f"\r\n--{boundary}--\r\n".encode()
        )
        request = self.make_request(
            body,
            content_type=f"multipart/form-data; boundary={boundary}".encode(),
            content_length=len(body),
        )
        with self.settings(
            DATA_UPLOAD_MAX_MEMORY_SIZE=10, FILE_UPLOAD_MAX_MEMORY_SIZE=10
        ):
            files = request.FILES
        self.assertEqual(len(files), 1)
        uploaded = files["file"]
        self.addCleanup(uploaded.close)
        self.assertEqual(uploaded.read(), file_content)

    async def test_read_body_buffers_all_chunks(self):
        # read_body() consumes all chunks regardless of
        # DATA_UPLOAD_MAX_MEMORY_SIZE; the limit is enforced later when
        # HttpRequest.body is accessed.
        chunks = [
            {"type": "http.request", "body": b"x" * 10, "more_body": True},
            {"type": "http.request", "body": b"y" * 10, "more_body": True},
            {"type": "http.request", "body": b"z" * 10, "more_body": False},
        ]

        async def receive():
            return chunks.pop(0)

        handler = ASGIHandler()
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=15):
            body_file = await handler.read_body(receive)
            self.addCleanup(body_file.close)

        self.assertEqual(len(chunks), 0)  # All chunks were consumed.
        body_file.seek(0)
        self.assertEqual(body_file.read(), b"x" * 10 + b"y" * 10 + b"z" * 10)

    async def test_read_body_multipart_not_limited(self):
        # All chunks are consumed regardless of DATA_UPLOAD_MAX_MEMORY_SIZE;
        # multipart size enforcement happens inside MultiPartParser, not here.
        chunks = [
            {"type": "http.request", "body": b"x" * 10, "more_body": True},
            {"type": "http.request", "body": b"y" * 10, "more_body": True},
            {"type": "http.request", "body": b"z" * 10, "more_body": False},
        ]

        async def receive():
            return chunks.pop(0)

        handler = ASGIHandler()
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=15):
            body_file = await handler.read_body(receive)
            self.addCleanup(body_file.close)

        self.assertEqual(len(chunks), 0)  # All chunks were consumed.
        body_file.seek(0)
        self.assertEqual(body_file.read(), b"x" * 10 + b"y" * 10 + b"z" * 10)
