from django.core.handlers.wsgi import WSGIHandler
from django.core import signals
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.utils import six


class HandlerTests(TestCase):

    # Mangle settings so the handler will fail
    @override_settings(MIDDLEWARE_CLASSES=42)
    def test_lock_safety(self):
        """
        Tests for bug #11193 (errors inside middleware shouldn't leave
        the initLock locked).
        """
        # Try running the handler, it will fail in load_middleware
        handler = WSGIHandler()
        self.assertEqual(handler.initLock.locked(), False)
        with self.assertRaises(Exception):
            handler(None, None)
        self.assertEqual(handler.initLock.locked(), False)

    def test_bad_path_info(self):
        """Tests for bug #15672 ('request' referenced before assignment)"""
        environ = RequestFactory().get('/').environ
        environ['PATH_INFO'] = '\xed'
        handler = WSGIHandler()
        response = handler(environ, lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)


class SignalsTests(TestCase):
    urls = 'regressiontests.handlers.urls'

    def setUp(self):
        self.signals = []
        signals.request_started.connect(self.register_started)
        signals.request_finished.connect(self.register_finished)

    def tearDown(self):
        signals.request_started.disconnect(self.register_started)
        signals.request_finished.disconnect(self.register_finished)

    def register_started(self, **kwargs):
        self.signals.append('started')

    def register_finished(self, **kwargs):
        self.signals.append('finished')

    def test_request_signals(self):
        response = self.client.get('/regular/')
        self.assertEqual(self.signals, ['started', 'finished'])
        self.assertEqual(response.content, b"regular content")

    def test_request_signals_streaming_response(self):
        response = self.client.get('/streaming/')
        self.assertEqual(self.signals, ['started'])
        self.assertEqual(b''.join(response.streaming_content), b"streaming content")
        self.assertEqual(self.signals, ['started', 'finished'])
