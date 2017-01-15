from django.conf.urls import url
from django.http import Http404, HttpResponse
from django.utils.decorators import (
    middleware_decorator, middleware_decorator_with_args)
from django.template import engines
from django.template.response import TemplateResponse
from django.test import override_settings, SimpleTestCase


class AnnotateMiddleware(object):
    """A middleware that annotates request/response to help with test assertions."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.call_reached = True
        response.call_reached_with_content = response.content
        return response


class ExceptionMiddleware(AnnotateMiddleware):
    def process_exception(self, request, exception):
        return HttpResponse('Exception handled.')


class ViewMiddleware(AnnotateMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        return HttpResponse('Processed view %s.' % view_func.__name__)


class TemplateResponseMiddleware(AnnotateMiddleware):
    def process_template_response(self, request, response):
        response.context_data['status'] = 'processed'
        return response


class MiddlewareA(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        calls = getattr(response, 'calls', [])
        calls.append(self.__class__.__name__)
        response.calls = calls
        return response


class MiddlewareB(MiddlewareA):
    pass


class NotFoundMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raise Http404()


class ArgsMiddleware(object):
    def __init__(self, get_response, arg1, arg2):
        self.get_response = get_response
        self.arg1 = arg1
        self.arg2 = arg2

    def __call__(self, request):
        response = self.get_response(request)
        response.middleware_args = (self.arg1, self.arg2)
        return response


deco = middleware_decorator(AnnotateMiddleware)
exc_deco = middleware_decorator(ExceptionMiddleware)
view_deco = middleware_decorator(ViewMiddleware)
template_response_deco = middleware_decorator(TemplateResponseMiddleware)
raising_deco = middleware_decorator(NotFoundMiddleware)
deco_a = middleware_decorator(MiddlewareA)
deco_b = middleware_decorator(MiddlewareB)
args_deco = middleware_decorator_with_args(ArgsMiddleware)


class MiddlewareDecoratorTests(SimpleTestCase):
    def get(self, view):
        with override_settings(ROOT_URLCONF=(url(r'^$', view),)):
            return self.client.get('/')

    def assertResponse(self, response, status, content):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.content, content)
        self.assertEqual(getattr(response, 'call_reached_with_content', ''), content)

    @property
    def ok_view(self):
        def ok_view(request):
            return HttpResponse("All ok.")
        return ok_view

    @property
    def template_response_view(self):
        def template_response_view(request):
            template = engines['django'].from_string("Template response {{ status }}.")
            return TemplateResponse(request, template, context={'status': "ok"})
        return template_response_view

    @property
    def class_view(self):
        class ClassView(object):
            def __call__(self, request):
                return HttpResponse("All ok.")

        return ClassView()

    @property
    def error_view(self):
        def error_view(request):
            raise Exception("Oops.")
        return error_view

    @property
    def not_found_view(self):
        def not_found_view(request):
            raise Http404()
        return not_found_view

    def test_request_response(self):
        """Middleware sees the request and response in its __call__."""
        response = self.get(deco(self.ok_view))
        self.assertResponse(response, 200, b'All ok.')

    def test_class_view(self):
        """Middleware decorator can decorate a class-based view."""
        response = self.get(deco(self.class_view))
        self.assertResponse(response, 200, b'All ok.')

    def test_template_response_rendered(self):
        """Middleware is called outside template-response rendering."""
        response = self.get(deco(self.template_response_view))
        self.assertResponse(response, 200, b'Template response ok.')

    def test_process_view(self):
        """Middleware process_view is called and can return a response."""
        response = self.get(view_deco(self.ok_view))
        self.assertResponse(response, 200, b'Processed view ok_view.')

    def test_process_template_response(self):
        """Middleware process_template_response can modify response pre-render."""
        response = self.get(template_response_deco(self.template_response_view))
        self.assertResponse(response, 200, b'Template response processed.')

    def test_process_exception(self):
        """Middleware can catch an exception and return a response."""
        response = self.get(exc_deco(self.error_view))
        self.assertResponse(response, 200, b'Exception handled.')

    @override_settings(MIDDLEWARE=['utils_tests.test_middleware_decorator.MiddlewareA'])
    def test_decorator_inside_other_middleware(self):
        """Middleware decorator runs inside other MIDDLEWARE."""
        decorator = middleware_decorator(MiddlewareB)
        response = self.get(decorator(self.ok_view))
        self.assertEqual(response.calls, ['MiddlewareB', 'MiddlewareA'])

    def test_exceptions_converted_before(self):
        """Middleware decorator will get response, not exception."""
        response = self.get(deco(self.not_found_view))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.call_reached)

    @override_settings(MIDDLEWARE=['utils_tests.test_middleware_decorator.AnnotateMiddleware'])
    def test_exceptions_converted_after(self):
        """If middleware decorator raises exception, it is converted before next middleware."""
        response = self.get(raising_deco(self.ok_view))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.call_reached)

    def test_exceptions_converted_between(self):
        """If middleware decorator raises exception, it is converted before next decorator."""
        response = self.get(deco(raising_deco(self.ok_view)))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.call_reached)

    def test_decorator_middleware_ordering(self):
        """Inner-applied decorator results in inner-applied middleware."""
        response = self.get(deco_a(deco_b(self.ok_view)))
        self.assertEqual(response.calls, ['MiddlewareB', 'MiddlewareA'])

    def test_decorator_middleware_with_args(self):
        """Can create a decorator factory that accepts additional arguments."""
        response = self.get(args_deco('a', arg2='b')(self.ok_view))
        self.assertEqual(response.middleware_args, ('a', 'b'))
