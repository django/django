from django.http import HttpResponse
from django.middleware.doc import XViewMiddleware
from django.template import Template, Context
from django.template.response import TemplateResponse
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


class FullMiddleware(object):
    def process_request(self, request):
        request.process_request_reached = True

    def process_view(sef, request, view_func, view_args, view_kwargs):
        request.process_view_reached = True

    def process_template_response(self, request, response):
        request.process_template_response_reached = True
        return response

    def process_response(self, request, response):
        # This should never receive unrendered content.
        request.process_response_content = response.content
        request.process_response_reached = True
        return response

full_dec = decorator_from_middleware(FullMiddleware)


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

    def test_full_dec_normal(self):
        """
        Test that all methods of middleware are called for normal HttpResponses
        """

        @full_dec
        def normal_view(request):
            t = Template("Hello world")
            return HttpResponse(t.render(Context({})))

        request = self.rf.get('/')
        response = normal_view(request)
        self.assertTrue(getattr(request, 'process_request_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        # process_template_response must not be called for HttpResponse
        self.assertFalse(getattr(request, 'process_template_response_reached', False))
        self.assertTrue(getattr(request, 'process_response_reached', False))

    def test_full_dec_templateresponse(self):
        """
        Test that all methods of middleware are called for TemplateResponses in
        the right sequence.
        """

        @full_dec
        def template_response_view(request):
            t = Template("Hello world")
            return TemplateResponse(request, t, {})

        request = self.rf.get('/')
        response = template_response_view(request)
        self.assertTrue(getattr(request, 'process_request_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        self.assertTrue(getattr(request, 'process_template_response_reached', False))
        # response must not be rendered yet.
        self.assertFalse(response._is_rendered)
        # process_response must not be called until after response is rendered,
        # otherwise some decorators like csrf_protect and gzip_page will not
        # work correctly. See #16004
        self.assertFalse(getattr(request, 'process_response_reached', False))
        response.render()
        self.assertTrue(getattr(request, 'process_response_reached', False))
        # Check that process_response saw the rendered content
        self.assertEqual(request.process_response_content, "Hello world")
