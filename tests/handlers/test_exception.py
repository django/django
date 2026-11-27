from django.core.handlers.wsgi import WSGIHandler
from django.core.signals import got_request_exception
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.client import (
    BOUNDARY,
    MULTIPART_CONTENT,
    FakePayload,
    encode_multipart,
)


class ExceptionHandlerTests(SimpleTestCase):
    def get_suspicious_environ(self):
        payload = FakePayload("a=1&a=2&a=3\r\n")
        return {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "CONTENT_LENGTH": len(payload),
            "wsgi.input": payload,
            "SERVER_NAME": "test",
            "SERVER_PORT": "8000",
        }

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=12)
    def test_data_upload_max_memory_size_exceeded(self):
        response = WSGIHandler()(self.get_suspicious_environ(), lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FIELDS=2)
    def test_data_upload_max_number_fields_exceeded(self):
        response = WSGIHandler()(self.get_suspicious_environ(), lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FILES=2)
    def test_data_upload_max_number_files_exceeded(self):
        payload = FakePayload(
            encode_multipart(
                BOUNDARY,
                {
                    "a.txt": "Hello World!",
                    "b.txt": "Hello Django!",
                    "c.txt": "Hello Python!",
                },
            )
        )
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": MULTIPART_CONTENT,
            "CONTENT_LENGTH": len(payload),
            "wsgi.input": payload,
            "SERVER_NAME": "test",
            "SERVER_PORT": "8000",
        }

        response = WSGIHandler()(environ, lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)

    @override_settings(ROOT_URLCONF="handlers.urls")
    def test_uncaught_exception_survives_failing_signal_receiver(self):
        """
        response_for_exception() still produces a 500 response for the
        original exception even if a got_request_exception receiver itself
        raises (#21777).
        """

        def failing_receiver(sender, request, **kwargs):
            raise RuntimeError("receiver boom")

        got_request_exception.connect(failing_receiver)
        self.addCleanup(got_request_exception.disconnect, failing_receiver)

        environ = RequestFactory().get("/errored/").environ
        with self.assertLogs("django.dispatch", "ERROR"):
            response = WSGIHandler()(environ, lambda *a, **k: None)
        self.assertEqual(response.status_code, 500)

    @override_settings(ROOT_URLCONF="handlers.urls_error_handlers")
    def test_get_exception_response_survives_failing_signal_receiver(self):
        """
        get_exception_response() still produces a 500 response when the
        error-handler callback raises, even if a got_request_exception
        receiver itself raises (#21777).
        """

        def failing_receiver(sender, request, **kwargs):
            raise RuntimeError("receiver boom")

        got_request_exception.connect(failing_receiver)
        self.addCleanup(got_request_exception.disconnect, failing_receiver)

        environ = RequestFactory().get("/does-not-exist/").environ
        with self.assertLogs("django.dispatch", "ERROR"):
            response = WSGIHandler()(environ, lambda *a, **k: None)
        self.assertEqual(response.status_code, 500)
