from io import BytesIO

from django.core.handlers.wsgi import WSGIHandler, WSGIRequest
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


class TestWSGIRoutingArgsAccessors(TestCase):
    
    base_environ = {'REQUEST_METHOD': 'GET', 'wsgi.input': BytesIO(b'')}
    
    def test_no_routing_args(self):
        request = WSGIRequest(self.base_environ.copy())
        self.assertEqual((), request.POSITIONAL_PATH_ARGS)
        self.assertEqual({}, request.NAMED_PATH_ARGS)
    
    def test_setting_first_time(self):
        # Positional args
        request1 = WSGIRequest(self.base_environ.copy())
        positional_args = ("hello-world", 33)
        request1.POSITIONAL_PATH_ARGS = positional_args
        self.assertEqual(
            positional_args,
            request1.environ['wsgiorg.routing_args'][0],
            )
        
        # Named args
        request2 = WSGIRequest(self.base_environ.copy())
        named_args = {'article-slug': "hello-world", 'comment-id': 33}
        request2.NAMED_PATH_ARGS = named_args
        self.assertEqual(
            named_args,
            request2.environ['wsgiorg.routing_args'][1],
            )
    
    def test_setting_subsequent_times(self):
        original_routing_args = (("hello-world", ), {'comment-id': 33})
        environ = self.base_environ.copy()
        environ['wsgiorg.routing_args'] = original_routing_args
        request = WSGIRequest(environ)
        
        # Override positional arguments; named ones must be preserved
        new_positional_args = ("international", "hello-world")
        request.POSITIONAL_PATH_ARGS = new_positional_args
        self.assertEqual(
            (new_positional_args, original_routing_args[1]),
            request.environ['wsgiorg.routing_args'],
            )
        
        # Override named arguments; positional ones must be preserved
        new_named_args = {'article-slug': "hello-world"}
        request.NAMED_PATH_ARGS = new_named_args
        self.assertEqual(
            (new_positional_args, new_named_args),
            request.environ['wsgiorg.routing_args'],
            )
    
    def test_getting_when_set(self):
        original_routing_args = (("hello-world", ), {'comment-id': 33})
        environ = self.base_environ.copy()
        environ['wsgiorg.routing_args'] = original_routing_args
        request = WSGIRequest(environ)
        
        self.assertEqual(original_routing_args[0], request.POSITIONAL_PATH_ARGS)
        self.assertEqual(original_routing_args[1], request.NAMED_PATH_ARGS)
    
    def test_getting_when_not_set(self):
        request = WSGIRequest(self.base_environ.copy())
        self.assertEqual((), request.POSITIONAL_PATH_ARGS)
        self.assertEqual({}, request.NAMED_PATH_ARGS)
