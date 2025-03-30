import asyncio
import sys
import threading
import time
from pathlib import Path

from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from django.core.exceptions import RequestDataTooBig
from django.core.handlers.asgi import ASGIHandler, ASGIRequest
from django.core.signals import request_finished, request_started
from django.db import close_old_connections
from django.http import HttpResponse, StreamingHttpResponse
from django.test import (
    AsyncRequestFactory,
    SimpleTestCase,
    ignore_warnings,
    modify_settings,
    override_settings,
)
from django.urls import path
from django.utils.http import http_date
from django.views.decorators.csrf import csrf_exempt

from .urls import sync_waiter, test_filename

TEST_STATIC_ROOT = Path(__file__).parent / "project" / "static"


class SignalHandler:
    """Helper class to track threads and kwargs when signals are dispatched."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def __call__(self, signal, **kwargs):
        self.calls.append({"thread": threading.current_thread(), "kwargs": kwargs})


@override_settings(ROOT_URLCONF="asgi.urls")
class ASGITest(SimpleTestCase):
    async_request_factory = AsyncRequestFactory()

    def setUp(self):
        request_started.disconnect(close_old_connections)
        self.addCleanup(request_started.connect, close_old_connections)

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
    # FileResponse as an async iterator. With a sync iterator
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

    async def test_create_request_error(self):
        # Track request_finished signal.
        signal_handler = SignalHandler()
        request_finished.connect(signal_handler)
        self.addCleanup(request_finished.disconnect, signal_handler)

        # Request class that always fails creation with RequestDataTooBig.
        class TestASGIRequest(ASGIRequest):

            def __init__(self, scope, body_file):
                super().__init__(scope, body_file)
                raise RequestDataTooBig()

        # Handler to use the custom request class.
        class TestASGIHandler(ASGIHandler):
            request_class = TestASGIRequest

        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(path="/not-important/")
        communicator = ApplicationCommunicator(application, scope)

        # Initiate request.
        await communicator.send_input({"type": "http.request"})
        # Give response.close() time to finish.
        await communicator.wait()

        self.assertEqual(len(signal_handler.calls), 1)
        self.assertNotEqual(
            signal_handler.calls[0]["thread"], threading.current_thread()
        )

    async def test_cancel_post_request_with_sync_processing(self):
        """
        The request.body object should be available and readable in view
        code, even if the ASGIHandler cancels processing part way through.
        """
        loop = asyncio.get_event_loop()
        # Events to monitor the view processing from the parent test code.
        view_started_event = asyncio.Event()
        view_finished_event = asyncio.Event()
        # Record received request body or exceptions raised in the test view
        outcome = []

        # This view will run in a new thread because it is wrapped in
        # sync_to_async. The view consumes the POST body data after a short
        # delay. The test will cancel the request using http.disconnect during
        # the delay, but because this is a sync view the code runs to
        # completion. There should be no exceptions raised inside the view
        # code.
        @csrf_exempt
        @sync_to_async
        def post_view(request):
            try:
                loop.call_soon_threadsafe(view_started_event.set)
                time.sleep(0.1)
                # Do something to read request.body after pause
                outcome.append({"request_body": request.body})
                return HttpResponse("ok")
            except Exception as e:
                outcome.append({"exception": e})
            finally:
                loop.call_soon_threadsafe(view_finished_event.set)

        # Request class to use the view.
        class TestASGIRequest(ASGIRequest):
            urlconf = (path("post/", post_view),)

        # Handler to use request class.
        class TestASGIHandler(ASGIHandler):
            request_class = TestASGIRequest

        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(
            method="POST",
            path="/post/",
        )
        communicator = ApplicationCommunicator(application, scope)

        await communicator.send_input({"type": "http.request", "body": b"Body data!"})

        # Wait until the view code has started, then send http.disconnect.
        await view_started_event.wait()
        await communicator.send_input({"type": "http.disconnect"})
        # Wait until view code has finished.
        await view_finished_event.wait()
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output()

        self.assertEqual(outcome, [{"request_body": b"Body data!"}])

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

    async def test_disconnect_both_return(self):
        # Force both the disconnect listener and the task that sends the
        # response to finish at the same time.
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request", "body": b"some body"})
        # Fetch response headers (this yields to asyncio and causes
        # ASGHandler.send_response() to dump the body of the response in the
        # queue).
        await communicator.receive_output()
        # Fetch response body (there's already some data queued up, so this
        # doesn't actually yield to the event loop, it just succeeds
        # instantly).
        await communicator.receive_output()
        # Send disconnect at the same time that response finishes (this just
        # puts some info in a queue, it doesn't have to yield to the event
        # loop).
        await communicator.send_input({"type": "http.disconnect"})
        # Waiting for the communicator _does_ yield to the event loop, since
        # ASGIHandler.send_response() is still waiting to do response.close().
        # It so happens that there are enough remaining yield points in both
        # tasks that they both finish while the loop is running.
        await communicator.wait()

    async def test_disconnect_with_body(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request", "body": b"some body"})
        await communicator.send_input({"type": "http.disconnect"})
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output()

    async def test_assert_in_listen_for_disconnect(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        await communicator.send_input({"type": "http.not_a_real_message"})
        msg = "Invalid ASGI message after request body: http.not_a_real_message"
        with self.assertRaisesMessage(AssertionError, msg):
            await communicator.wait()

    async def test_delayed_disconnect_with_body(self):
        application = get_asgi_application()
        scope = self.async_request_factory._base_scope(path="/delayed_hello/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request", "body": b"some body"})
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
        # Track request_started and request_finished signals.
        signal_handler = SignalHandler()
        request_started.connect(signal_handler)
        self.addCleanup(request_started.disconnect, signal_handler)
        request_finished.connect(signal_handler)
        self.addCleanup(request_finished.disconnect, signal_handler)

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
        self.assertEqual(len(signal_handler.calls), 2)
        request_started_call, request_finished_call = signal_handler.calls
        self.assertEqual(
            request_started_call["thread"], request_finished_call["thread"]
        )

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

    async def test_asyncio_cancel_error(self):
        view_started = asyncio.Event()
        # Flag to check if the view was cancelled.
        view_did_cancel = False
        # Track request_finished signal.
        signal_handler = SignalHandler()
        request_finished.connect(signal_handler)
        self.addCleanup(request_finished.disconnect, signal_handler)

        # A view that will listen for the cancelled error.
        async def view(request):
            nonlocal view_did_cancel
            view_started.set()
            try:
                await asyncio.sleep(0.1)
                return HttpResponse("Hello World!")
            except asyncio.CancelledError:
                # Set the flag.
                view_did_cancel = True
                raise

        # Request class to use the view.
        class TestASGIRequest(ASGIRequest):
            urlconf = (path("cancel/", view),)

        # Handler to use request class.
        class TestASGIHandler(ASGIHandler):
            request_class = TestASGIRequest

        # Request cycle should complete since no disconnect was sent.
        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(path="/cancel/")
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
        self.assertIs(view_did_cancel, False)
        # Exactly one call to request_finished handler.
        self.assertEqual(len(signal_handler.calls), 1)
        handler_call = signal_handler.calls.pop()
        # It was NOT on the async thread.
        self.assertNotEqual(handler_call["thread"], threading.current_thread())
        # The signal sender is the handler class.
        self.assertEqual(handler_call["kwargs"], {"sender": TestASGIHandler})
        view_started.clear()

        # Request cycle with a disconnect before the view can respond.
        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(path="/cancel/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        # Let the view actually start.
        await view_started.wait()
        # Disconnect the client.
        await communicator.send_input({"type": "http.disconnect"})
        # The handler should not send a response.
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output()
        await communicator.wait()
        self.assertIs(view_did_cancel, True)
        # Exactly one call to request_finished handler.
        self.assertEqual(len(signal_handler.calls), 1)
        handler_call = signal_handler.calls.pop()
        # It was NOT on the async thread.
        self.assertNotEqual(handler_call["thread"], threading.current_thread())
        # The signal sender is the handler class.
        self.assertEqual(handler_call["kwargs"], {"sender": TestASGIHandler})

    async def test_asyncio_streaming_cancel_error(self):
        # Similar to test_asyncio_cancel_error(), but during a streaming
        # response.
        view_did_cancel = False
        # Track request_finished signals.
        signal_handler = SignalHandler()
        request_finished.connect(signal_handler)
        self.addCleanup(request_finished.disconnect, signal_handler)

        async def streaming_response():
            nonlocal view_did_cancel
            try:
                await asyncio.sleep(0.2)
                yield b"Hello World!"
            except asyncio.CancelledError:
                # Set the flag.
                view_did_cancel = True
                raise

        async def view(request):
            return StreamingHttpResponse(streaming_response())

        class TestASGIRequest(ASGIRequest):
            urlconf = (path("cancel/", view),)

        class TestASGIHandler(ASGIHandler):
            request_class = TestASGIRequest

        # With no disconnect, the request cycle should complete in the same
        # manner as the non-streaming response.
        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(path="/cancel/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        response_body = await communicator.receive_output()
        self.assertEqual(response_body["type"], "http.response.body")
        self.assertEqual(response_body["body"], b"Hello World!")
        await communicator.wait()
        self.assertIs(view_did_cancel, False)
        # Exactly one call to request_finished handler.
        self.assertEqual(len(signal_handler.calls), 1)
        handler_call = signal_handler.calls.pop()
        # It was NOT on the async thread.
        self.assertNotEqual(handler_call["thread"], threading.current_thread())
        # The signal sender is the handler class.
        self.assertEqual(handler_call["kwargs"], {"sender": TestASGIHandler})

        # Request cycle with a disconnect.
        application = TestASGIHandler()
        scope = self.async_request_factory._base_scope(path="/cancel/")
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        # Fetch the start of response so streaming can begin
        self.assertEqual(response_start["type"], "http.response.start")
        self.assertEqual(response_start["status"], 200)
        await asyncio.sleep(0.1)
        # Now disconnect the client.
        await communicator.send_input({"type": "http.disconnect"})
        # This time the handler should not send a response.
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output()
        await communicator.wait()
        self.assertIs(view_did_cancel, True)
        # Exactly one call to request_finished handler.
        self.assertEqual(len(signal_handler.calls), 1)
        handler_call = signal_handler.calls.pop()
        # It was NOT on the async thread.
        self.assertNotEqual(handler_call["thread"], threading.current_thread())
        # The signal sender is the handler class.
        self.assertEqual(handler_call["kwargs"], {"sender": TestASGIHandler})

    async def test_streaming(self):
        scope = self.async_request_factory._base_scope(
            path="/streaming/", query_string=b"sleep=0.001"
        )
        application = get_asgi_application()
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        # Fetch http.response.start.
        await communicator.receive_output(timeout=1)
        # Fetch the 'first' and 'last'.
        first_response = await communicator.receive_output(timeout=1)
        self.assertEqual(first_response["body"], b"first\n")
        second_response = await communicator.receive_output(timeout=1)
        self.assertEqual(second_response["body"], b"last\n")
        # Fetch the rest of the response so that coroutines are cleaned up.
        await communicator.receive_output(timeout=1)
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output(timeout=1)

    async def test_streaming_disconnect(self):
        scope = self.async_request_factory._base_scope(
            path="/streaming/", query_string=b"sleep=0.1"
        )
        application = get_asgi_application()
        communicator = ApplicationCommunicator(application, scope)
        await communicator.send_input({"type": "http.request"})
        await communicator.receive_output(timeout=1)
        first_response = await communicator.receive_output(timeout=1)
        self.assertEqual(first_response["body"], b"first\n")
        # Disconnect the client.
        await communicator.send_input({"type": "http.disconnect"})
        # 'last\n' isn't sent.
        with self.assertRaises(asyncio.TimeoutError):
            await communicator.receive_output(timeout=0.2)
