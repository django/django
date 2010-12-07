import sys

from django.conf import settings
from django.core.signals import got_request_exception
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.template import Template
from django.test import TestCase

class TestException(Exception):
    pass

# A middleware base class that tracks which methods have been called

class TestMiddleware(object):
    def __init__(self):
        self.process_request_called = False
        self.process_view_called = False
        self.process_response_called = False
        self.process_template_response_called = False
        self.process_exception_called = False

    def process_request(self, request):
        self.process_request_called = True

    def process_view(self, request, view_func, view_args, view_kwargs):
        self.process_view_called = True

    def process_template_response(self, request, response):
        self.process_template_response_called = True
        return response

    def process_response(self, request, response):
        self.process_response_called = True
        return response

    def process_exception(self, request, exception):
        self.process_exception_called = True

# Middleware examples that do the right thing

class RequestMiddleware(TestMiddleware):
    def process_request(self, request):
        super(RequestMiddleware, self).process_request(request)
        return HttpResponse('Request Middleware')

class ViewMiddleware(TestMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        super(ViewMiddleware, self).process_view(request, view_func, view_args, view_kwargs)
        return HttpResponse('View Middleware')

class ResponseMiddleware(TestMiddleware):
    def process_response(self, request, response):
        super(ResponseMiddleware, self).process_response(request, response)
        return HttpResponse('Response Middleware')

class TemplateResponseMiddleware(TestMiddleware):
    def process_template_response(self, request, response):
        super(TemplateResponseMiddleware, self).process_template_response(request, response)
        return TemplateResponse(request, Template('Template Response Middleware'))

class ExceptionMiddleware(TestMiddleware):
    def process_exception(self, request, exception):
        super(ExceptionMiddleware, self).process_exception(request, exception)
        return HttpResponse('Exception Middleware')


# Sample middlewares that raise exceptions

class BadRequestMiddleware(TestMiddleware):
    def process_request(self, request):
        super(BadRequestMiddleware, self).process_request(request)
        raise TestException('Test Request Exception')

class BadViewMiddleware(TestMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        super(BadViewMiddleware, self).process_view(request, view_func, view_args, view_kwargs)
        raise TestException('Test View Exception')

class BadTemplateResponseMiddleware(TestMiddleware):
    def process_template_response(self, request, response):
        super(BadTemplateResponseMiddleware, self).process_template_response(request, response)
        raise TestException('Test Template Response Exception')

class BadResponseMiddleware(TestMiddleware):
    def process_response(self, request, response):
        super(BadResponseMiddleware, self).process_response(request, response)
        raise TestException('Test Response Exception')

class BadExceptionMiddleware(TestMiddleware):
    def process_exception(self, request, exception):
        super(BadExceptionMiddleware, self).process_exception(request, exception)
        raise TestException('Test Exception Exception')


class BaseMiddlewareExceptionTest(TestCase):
    def setUp(self):
        self.exceptions = []
        got_request_exception.connect(self._on_request_exception)
        self.client.handler.load_middleware()

    def tearDown(self):
        got_request_exception.disconnect(self._on_request_exception)
        self.exceptions = []

    def _on_request_exception(self, sender, request, **kwargs):
        self.exceptions.append(sys.exc_info())

    def _add_middleware(self, middleware):
        self.client.handler._request_middleware.insert(0, middleware.process_request)
        self.client.handler._view_middleware.insert(0, middleware.process_view)
        self.client.handler._template_response_middleware.append(middleware.process_template_response)
        self.client.handler._response_middleware.append(middleware.process_response)
        self.client.handler._exception_middleware.append(middleware.process_exception)

    def assert_exceptions_handled(self, url, errors, extra_error=None):
        try:
            response = self.client.get(url)
        except TestException, e:
            # Test client intentionally re-raises any exceptions being raised
            # during request handling. Hence actual testing that exception was
            # properly handled is done by relying on got_request_exception
            # signal being sent.
            pass
        except Exception, e:
            if type(extra_error) != type(e):
                self.fail("Unexpected exception: %s" % e)
        self.assertEquals(len(self.exceptions), len(errors))
        for i, error in enumerate(errors):
            exception, value, tb = self.exceptions[i]
            self.assertEquals(value.args, (error, ))

    def assert_middleware_usage(self, middleware, request, view, template_response, response, exception):
        self.assertEqual(middleware.process_request_called, request)
        self.assertEqual(middleware.process_view_called, view)
        self.assertEqual(middleware.process_template_response_called, template_response)
        self.assertEqual(middleware.process_response_called, response)
        self.assertEqual(middleware.process_exception_called, exception)


class MiddlewareTests(BaseMiddlewareExceptionTest):

    def test_process_request_middleware(self):
        pre_middleware = TestMiddleware()
        middleware = RequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(middleware,      True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_middleware(self):
        pre_middleware = TestMiddleware()
        middleware = ViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(middleware,      True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_middleware(self):
        pre_middleware = TestMiddleware()
        middleware = ResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_template_response_middleware(self):
        pre_middleware = TestMiddleware()
        middleware = TemplateResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/template_response/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, True, True, False)
        self.assert_middleware_usage(middleware,      True, True, True, True, False)
        self.assert_middleware_usage(post_middleware, True, True, True, True, False)

    def test_process_exception_middleware(self):
        pre_middleware = TestMiddleware()
        middleware = ExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_request_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        middleware = RequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(middleware,      True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        middleware = ViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(middleware,      True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_template_response_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        middleware = TemplateResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_response_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        middleware = ResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_exception_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        middleware = ExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_request_middleware_exception(self):
        pre_middleware = TestMiddleware()
        middleware = RequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(middleware,      True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_middleware_exception(self):
        pre_middleware = TestMiddleware()
        middleware = ViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(middleware,      True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_middleware_exception(self):
        pre_middleware = TestMiddleware()
        middleware = ResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', ['Error in view'], Exception())

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_exception_middleware_exception(self):
        pre_middleware = TestMiddleware()
        middleware = ExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_request_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        middleware = RequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(middleware,      True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        middleware = ViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(middleware,      True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        middleware = ResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [
                "The view regressiontests.middleware_exceptions.views.null_view didn't return an HttpResponse object.",
            ],
            ValueError())

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_exception_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        middleware = ExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [
                "The view regressiontests.middleware_exceptions.views.null_view didn't return an HttpResponse object."
            ],
            ValueError())

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_request_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        middleware = RequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(middleware,      True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        middleware = ViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(middleware,      True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        middleware = ResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_exception_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        middleware = ExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(middleware,      True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_template_response_error(self):
        middleware = TestMiddleware()
        self._add_middleware(middleware)
        self.assert_exceptions_handled('/middleware_exceptions/template_response_error/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(middleware, True, True, True, True, False)


class BadMiddlewareTests(BaseMiddlewareExceptionTest):

    def test_process_request_bad_middleware(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadRequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', ['Test Request Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_bad_middleware(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', ['Test View Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_template_response_bad_middleware(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadTemplateResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/template_response/', ['Test Template Response Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, False)
        self.assert_middleware_usage(bad_middleware,  True, True, True,  False, False)
        self.assert_middleware_usage(post_middleware, True, True, True,  False, False)

    def test_process_response_bad_middleware(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', ['Test Response Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True,  False)
        self.assert_middleware_usage(post_middleware, True, True, False, True,  False)

    def test_process_exception_bad_middleware(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/view/', [])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_request_bad_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadRequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', ['Test Request Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_bad_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', ['Test View Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_bad_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', ['Test Response Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, True)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True,  True)
        self.assert_middleware_usage(post_middleware, True, True, False, True,  True)

    def test_process_exception_bad_middleware_not_found(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/not_found/', ['Test Exception Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_request_bad_middleware_exception(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadRequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', ['Test Request Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_bad_middleware_exception(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', ['Test View Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_bad_middleware_exception(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', ['Error in view', 'Test Response Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, True)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True,  True)
        self.assert_middleware_usage(post_middleware, True, True, False, True,  True)

    def test_process_exception_bad_middleware_exception(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/error/', ['Test Exception Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)

    def test_process_request_bad_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadRequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', ['Test Request Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_bad_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', ['Test View Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_bad_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [
                "The view regressiontests.middleware_exceptions.views.null_view didn't return an HttpResponse object.",
                'Test Response Exception'
            ])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True,  False)
        self.assert_middleware_usage(post_middleware, True, True, False, True,  False)

    def test_process_exception_bad_middleware_null_view(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/null_view/', [
                "The view regressiontests.middleware_exceptions.views.null_view didn't return an HttpResponse object."
            ],
            ValueError())

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(post_middleware, True, True, False, True, False)

    def test_process_request_bad_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadRequestMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', ['Test Request Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True,  False, False, True, False)
        self.assert_middleware_usage(post_middleware, False, False, False, True, False)

    def test_process_view_bad_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadViewMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', ['Test View Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True,  False, True, False)
        self.assert_middleware_usage(post_middleware, True, False, False, True, False)

    def test_process_response_bad_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadResponseMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', ['Test Response Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, False, True)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True,  True)
        self.assert_middleware_usage(post_middleware, True, True, False, True,  True)

    def test_process_exception_bad_middleware_permission_denied(self):
        pre_middleware = TestMiddleware()
        bad_middleware = BadExceptionMiddleware()
        post_middleware = TestMiddleware()
        self._add_middleware(post_middleware)
        self._add_middleware(bad_middleware)
        self._add_middleware(pre_middleware)
        self.assert_exceptions_handled('/middleware_exceptions/permission_denied/', ['Test Exception Exception'])

        # Check that the right middleware methods have been invoked
        self.assert_middleware_usage(pre_middleware,  True, True, False, True, False)
        self.assert_middleware_usage(bad_middleware,  True, True, False, True, True)
        self.assert_middleware_usage(post_middleware, True, True, False, True, True)


_missing = object()
class RootUrlconfTests(TestCase):
    def test_missing_root_urlconf(self):
        try:
            original_ROOT_URLCONF = settings.ROOT_URLCONF
            del settings.ROOT_URLCONF
        except AttributeError:
            original_ROOT_URLCONF = _missing
        self.assertRaises(AttributeError,
            self.client.get, "/middleware_exceptions/view/"
        )

        if original_ROOT_URLCONF is not _missing:
            settings.ROOT_URLCONF = original_ROOT_URLCONF
