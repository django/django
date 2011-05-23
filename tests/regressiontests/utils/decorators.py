from django.http import HttpResponse
from django.middleware.doc import XViewMiddleware
from django.test import TestCase, RequestFactory
from django.utils.decorators import decorator_from_middleware


xview_dec = decorator_from_middleware(XViewMiddleware)


@xview_dec
def xview(request):
    return HttpResponse()


class ClassXView(object):
    def __call__(self, request):
        return HttpResponse()

class_xview = xview_dec(ClassXView())


class DecoratorFromMiddlewareTests(TestCase):
    """
    Tests for view decorators created using
    ``django.utils.decorators.decorator_from_middleware``.
    """
    rf = RequestFactory()

    def test_process_view_middleware(self):
        """
        Test a middleware that implements process_view.
        """
        xview(self.rf.get('/'))

    def test_callable_process_view_middleware(self):
        """
        Test a middleware that implements process_view, operating on a callable class.
        """
        class_xview(self.rf.get('/'))
