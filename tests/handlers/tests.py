from django.core.handlers.wsgi import WSGIHandler
from django.core.signals import request_started, request_finished
from django.db import close_old_connections, connection
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.test.utils import override_settings


class HandlerTests(TestCase):

    def setUp(self):
        request_started.disconnect(close_old_connections)

    def tearDown(self):
        request_started.connect(close_old_connections)

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


class TransactionsPerRequestTests(TransactionTestCase):
    urls = 'handlers.urls'

    def test_no_transaction(self):
        response = self.client.get('/in_transaction/')
        self.assertContains(response, 'False')

    def test_auto_transaction(self):
        old_atomic_requests = connection.settings_dict['ATOMIC_REQUESTS']
        try:
            connection.settings_dict['ATOMIC_REQUESTS'] = True
            response = self.client.get('/in_transaction/')
        finally:
            connection.settings_dict['ATOMIC_REQUESTS'] = old_atomic_requests
        self.assertContains(response, 'True')

    def test_no_auto_transaction(self):
        old_atomic_requests = connection.settings_dict['ATOMIC_REQUESTS']
        try:
            connection.settings_dict['ATOMIC_REQUESTS'] = True
            response = self.client.get('/not_in_transaction/')
        finally:
            connection.settings_dict['ATOMIC_REQUESTS'] = old_atomic_requests
        self.assertContains(response, 'False')


class SignalsTests(TestCase):
    urls = 'handlers.urls'

    def setUp(self):
        self.signals = []
        request_started.connect(self.register_started)
        request_finished.connect(self.register_finished)

    def tearDown(self):
        request_started.disconnect(self.register_started)
        request_finished.disconnect(self.register_finished)

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


class HandlerSuspiciousOpsTest(TestCase):
    urls = 'handlers.urls'

    def test_suspiciousop_in_view_returns_400(self):
        response = self.client.get('/suspicious/')
        self.assertEqual(response.status_code, 400)
