from django.http import HttpResponse
from django.template import engines
from django.template.response import TemplateResponse
from django.test import RequestFactory, SimpleTestCase
from django.utils.decorators import classproperty, decorator_from_middleware


class ProcessViewMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        pass


process_view_dec = decorator_from_middleware(ProcessViewMiddleware)


@process_view_dec
def process_view(request):
    return HttpResponse()


class ClassProcessView(object):
    def __call__(self, request):
        return HttpResponse()


class_process_view = process_view_dec(ClassProcessView())


class FullMiddleware(object):
    def process_request(self, request):
        request.process_request_reached = True

    def process_view(self, request, view_func, view_args, view_kwargs):
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


class DecoratorFromMiddlewareTests(SimpleTestCase):
    """
    Tests for view decorators created using
    ``django.utils.decorators.decorator_from_middleware``.
    """
    rf = RequestFactory()

    def test_process_view_middleware(self):
        """
        Test a middleware that implements process_view.
        """
        process_view(self.rf.get('/'))

    def test_callable_process_view_middleware(self):
        """
        Test a middleware that implements process_view, operating on a callable class.
        """
        class_process_view(self.rf.get('/'))

    def test_full_dec_normal(self):
        """
        All methods of middleware are called for normal HttpResponses
        """
        @full_dec
        def normal_view(request):
            template = engines['django'].from_string("Hello world")
            return HttpResponse(template.render())

        request = self.rf.get('/')
        normal_view(request)
        self.assertTrue(getattr(request, 'process_request_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        # process_template_response must not be called for HttpResponse
        self.assertFalse(getattr(request, 'process_template_response_reached', False))
        self.assertTrue(getattr(request, 'process_response_reached', False))

    def test_full_dec_templateresponse(self):
        """
        All methods of middleware are called for TemplateResponses in
        the right sequence.
        """
        @full_dec
        def template_response_view(request):
            template = engines['django'].from_string("Hello world")
            return TemplateResponse(request, template)

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
        # process_response saw the rendered content
        self.assertEqual(request.process_response_content, b"Hello world")


class ClassPropertyTest(SimpleTestCase):
    def test_getter(self):
        class Foo(object):
            foo_attr = 123

            def __init__(self):
                self.foo_attr = 456

            @classproperty
            def foo(cls):
                return cls.foo_attr

        class Bar(object):
            bar = classproperty()

            @bar.getter
            def bar(cls):
                return 123

        self.assertEqual(Foo.foo, 123)
        self.assertEqual(Foo().foo, 123)
        self.assertEqual(Bar.bar, 123)
        self.assertEqual(Bar().bar, 123)

    def test_override_getter(self):
        class Foo(object):
            @classproperty
            def foo(cls):
                return 123

            @foo.getter
            def foo(cls):
                return 456

        self.assertEqual(Foo.foo, 456)
        self.assertEqual(Foo().foo, 456)
