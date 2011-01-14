from django.utils import unittest
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler

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

