import asyncio
import sys
import threading
from pathlib import Path
from unittest import skipIf

from asgiref.testing import ApplicationCommunicator

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from django.core.signals import request_finished, request_started
from django.db import close_old_connections
from django.test import (
    AsyncRequestFactory,
    SimpleTestCase,
    modify_settings,
    override_settings,
)
from django.utils.http import http_date

from .urls import sync_waiter, test_filename

TEST_STATIC_ROOT = Path(__file__).parent / "project" / "static"


@skipIf(
    sys.platform == "win32" and (3, 8, 0) < sys.version_info < (3, 8, 1),
    "https://bugs.python.org/issue38563",
)
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
