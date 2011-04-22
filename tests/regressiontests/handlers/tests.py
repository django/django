from django.utils import unittest
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.test import RequestFactory


class HandlerTests(unittest.TestCase):

    def test_lock_safety(self):
        """
        Tests for bug #11193 (errors inside middleware shouldn't leave
        the initLock locked).
        """
        # Mangle settings so the handler will fail
        old_middleware_classes = settings.MIDDLEWARE_CLASSES
        settings.MIDDLEWARE_CLASSES = 42
        # Try running the handler, it will fail in load_middleware
        handler = WSGIHandler()
        self.assertEqual(handler.initLock.locked(), False)
        try:
            handler(None, None)
        except:
            pass
        self.assertEqual(handler.initLock.locked(), False)
        # Reset settings
        settings.MIDDLEWARE_CLASSES = old_middleware_classes

    def test_bad_path_info(self):
        """Tests for bug #15672 ('request' referenced before assignment)"""
        environ = RequestFactory().get('/').environ
        environ['PATH_INFO'] = '\xed'
        handler = WSGIHandler()
        response = handler(environ, lambda *a, **k: None)
        self.assertEqual(response.status_code, 400)
