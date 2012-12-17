from django.core.handlers.wsgi import WSGIHandler
from django.test import RequestFactory
from django.test.utils import override_settings
from django.utils import six
from django.utils import unittest

class HandlerTests(unittest.TestCase):

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
