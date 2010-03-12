from django.test import TestCase

class DecoratorFromMiddlewareTests(TestCase):
    """
    Tests for view decorators created using
    ``django.utils.decorators.decorator_from_middleware``.
    """

    def test_process_view_middleware(self):
        """
        Test a middleware that implements process_view.
        """
        self.client.get('/utils/xview/')

    def test_callable_process_view_middleware(self):
        """
        Test a middleware that implements process_view, operating on a callable class.
        """
        self.client.get('/utils/class_xview/')
