from django.core.handlers.wsgi import WSGIHandler
from django.test import SimpleTestCase, override_settings
from django.test.client import FakePayload


class ExceptionHandlerTests(SimpleTestCase):

    def get_suspicious_environ(self):
        payload = FakePayload('a=1&a=2&a=3\r\n')
        return {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': len(payload),
            'wsgi.input': payload,
            'SERVER_NAME': 'test',
            'SERVER_PORT': '8000',
        }

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=12)
    def test_data_upload_max_memory_size_exceeded(self):
        response = WSGIHandler()(self.get_suspicious_environ(), lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FIELDS=2)
    def test_data_upload_max_number_fields_exceeded(self):
        response = WSGIHandler()(self.get_suspicious_environ(), lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)
