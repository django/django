from django.http import HttpResponse
from django.template import engines
from django.template.response import TemplateResponse
from django.test import RequestFactory, SimpleTestCase
from django.utils.decorators import (
    classproperty, decorator_from_middleware,
    decorator_from_middleware_with_args,
)
from django.utils.deprecation import MiddlewareMixin


class LegacyProcessViewMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        pass

legacy_process_view_dec = decorator_from_middleware(LegacyProcessViewMiddleware)


@legacy_process_view_dec
def legacy_process_view(request):
    return HttpResponse()


class ProcessViewMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        pass

process_view_dec = decorator_from_middleware(ProcessViewMiddleware)


@process_view_dec
def process_view(request):
    return HttpResponse()


class ClassProcessView(object):
    def __call__(self, request):
        return HttpResponse()

legacy_class_process_view = process_view_dec(ClassProcessView())
class_process_view = process_view_dec(ClassProcessView())


class LegacyFullMiddleware(object):
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

    def process_exception(self, request, exception):
        request.process_exception_reached = True
        return HttpResponse('exception caught')

legacy_full_dec = decorator_from_middleware(LegacyFullMiddleware)


class LegacyMiddlewareWithArg(object):
    def __init__(self, arg=None):
        self.arg = arg

    def process_request(self, request):
        request.middleware_got_arg = self.arg


legacy_with_arg_dec = decorator_from_middleware_with_args(LegacyMiddlewareWithArg)


class SomeViewException(Exception):
    pass


class FullMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.call_reached = True
        response = self.get_response(request)
        response.call_reached = True
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.process_view_reached = True

    def process_template_response(self, request, response):
        request.process_template_response_reached = True
        return response

    def process_exception(self, request, exception):
        request.process_exception_reached = True
        return HttpResponse('exception caught')

full_dec = decorator_from_middleware(FullMiddleware)


def function_middleware_factory(get_response):
    def middleware(request):
        request.call_reached = True
        response = get_response(request)
        response.call_reached = True
        return response

    return middleware

func_dec = decorator_from_middleware(function_middleware_factory)


def middleware_with_args(get_response, arg):
    def middleware(request):
        request.middleware_got_arg = arg
        return get_response(request)

    return middleware

func_with_args_dec = decorator_from_middleware_with_args(middleware_with_args)


class LegacyDecoratorFromMiddlewareTests(SimpleTestCase):
    """
    Tests for view decorators created using
    ``django.utils.decorators.decorator_from_middleware``.
    """
    rf = RequestFactory()

    def test_process_view_middleware(self):
        """
        Test a middleware that implements process_view.
        """
        legacy_process_view(self.rf.get('/'))

    def test_callable_process_view_middleware(self):
        """
        Test a middleware that implements process_view, operating on a callable class.
        """
        legacy_class_process_view(self.rf.get('/'))

    def test_process_exception(self):

        @legacy_full_dec
        def exception_view(request):
            raise Exception()

        request = self.rf.get('/')
        response = exception_view(request)
        self.assertEqual(response.content, b'exception caught')
        self.assertTrue(getattr(request, 'process_request_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        self.assertTrue(getattr(request, 'process_exception_reached', False))
        self.assertTrue(getattr(request, 'process_response_reached', False))

    def test_full_dec_normal(self):
        """
        Test that all methods of middleware are called for normal HttpResponses
        """

        @legacy_full_dec
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        normal_view(request)
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

        @legacy_full_dec
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
        # Check that process_response saw the rendered content
        self.assertEqual(request.process_response_content, b"Hello world")

    def test_templateresponse_middlewaremixin_back_compat(self):
        """
        An old-style middleware whose process_response assumes any
        TemplateResponse must be already rendered can inherit from
        MiddlewareMixin and still work.
        """

        class UpdatedLegacyFullMiddleware(MiddlewareMixin, LegacyFullMiddleware):
            pass

        dec = decorator_from_middleware(UpdatedLegacyFullMiddleware)

        @dec
        def template_response_view(request):
            template = engines['django'].from_string("Hello {{ name }}")
            return TemplateResponse(request, template, {'name': "Maria"})

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
        self.assertEqual(request.process_response_content, b"Hello Maria")

    def test_middleware_with_args(self):

        @legacy_with_arg_dec('foo')
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        normal_view(request)
        self.assertEqual(request.middleware_got_arg, 'foo')

    def test_middleware_with_args_none_given(self):

        @legacy_with_arg_dec()
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        normal_view(request)
        self.assertIs(request.middleware_got_arg, None)


class DecoratorFromMiddlewareTests(SimpleTestCase):
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

    def test_process_exception(self):
        """
        process_exception is called for view exceptions.
        """

        @full_dec
        def exception_view(request):
            raise Exception()

        request = self.rf.get('/')
        response = exception_view(request)
        self.assertEqual(response.content, b'exception caught')
        self.assertTrue(getattr(request, 'call_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        self.assertTrue(getattr(request, 'process_exception_reached', False))

    def test_full_dec_normal(self):
        """
        Applicable middleware methods are called for normal HttpResponses.
        """

        @full_dec
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        response = normal_view(request)
        self.assertTrue(getattr(request, 'call_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        # process_template_response must not be called for HttpResponse
        self.assertFalse(getattr(request, 'process_template_response_reached', False))
        self.assertTrue(getattr(response, 'call_reached', False))

    def test_full_dec_templateresponse(self):
        """
        All methods are called for TemplateResponses.
        """

        @full_dec
        def template_response_view(request):
            template = engines['django'].from_string("Hello world")
            return TemplateResponse(request, template)

        request = self.rf.get('/')
        response = template_response_view(request)
        self.assertTrue(getattr(request, 'call_reached', False))
        self.assertTrue(getattr(request, 'process_view_reached', False))
        self.assertTrue(getattr(request, 'process_template_response_reached', False))
        self.assertTrue(getattr(response, 'call_reached', False))

    def test_function_middleware_factory(self):

        @func_dec
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        response = normal_view(request)
        self.assertTrue(getattr(request, 'call_reached', False))
        self.assertTrue(getattr(response, 'call_reached', False))

    def test_middleware_with_args(self):

        @func_with_args_dec('foo')
        def normal_view(request):
            return HttpResponse("Hello world")

        request = self.rf.get('/')
        normal_view(request)
        self.assertEqual(request.middleware_got_arg, 'foo')


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
