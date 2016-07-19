from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import patch_logger

from . import middleware as mw


@override_settings(ROOT_URLCONF='middleware_exceptions.urls')
class MiddlewareTests(SimpleTestCase):
    def tearDown(self):
        mw.log = []

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.ProcessViewNoneMiddleware'])
    def test_process_view_return_none(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(mw.log, ['processed view normal_view'])
        self.assertEqual(response.content, b'OK')

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.ProcessViewMiddleware'])
    def test_process_view_return_response(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.content, b'Processed view normal_view')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.ProcessViewTemplateResponseMiddleware',
        'middleware_exceptions.middleware.LogMiddleware',
    ])
    def test_templateresponse_from_process_view_rendered(self):
        """
        TemplateResponses returned from process_view() must be rendered before
        being passed to any middleware that tries to access response.content,
        such as middleware_exceptions.middleware.LogMiddleware.
        """
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.content, b'Processed view normal_view\nProcessViewTemplateResponseMiddleware')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.ProcessViewTemplateResponseMiddleware',
        'middleware_exceptions.middleware.TemplateResponseMiddleware',
    ])
    def test_templateresponse_from_process_view_passed_to_process_template_response(self):
        """
        TemplateResponses returned from process_view() should be passed to any
        template response middleware.
        """
        response = self.client.get('/middleware_exceptions/view/')
        expected_lines = [
            b'Processed view normal_view',
            b'ProcessViewTemplateResponseMiddleware',
            b'TemplateResponseMiddleware',
        ]
        self.assertEqual(response.content, b'\n'.join(expected_lines))

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.TemplateResponseMiddleware'])
    def test_process_template_response(self):
        response = self.client.get('/middleware_exceptions/template_response/')
        self.assertEqual(response.content, b'template_response OK\nTemplateResponseMiddleware')

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.LogMiddleware'])
    def test_view_exception_converted_before_middleware(self):
        response = self.client.get('/middleware_exceptions/permission_denied/')
        self.assertEqual(mw.log, [(response.status_code, response.content)])
        self.assertEqual(response.status_code, 403)

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.ProcessExceptionMiddleware'])
    def test_view_exception_handled_by_process_exception(self):
        response = self.client.get('/middleware_exceptions/error/')
        self.assertEqual(response.content, b'Exception caught')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.ProcessExceptionLogMiddleware',
        'middleware_exceptions.middleware.ProcessExceptionMiddleware',
    ])
    def test_response_from_process_exception_short_circuits_remainder(self):
        response = self.client.get('/middleware_exceptions/error/')
        self.assertEqual(mw.log, [])
        self.assertEqual(response.content, b'Exception caught')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.LogMiddleware',
        'middleware_exceptions.middleware.NotFoundMiddleware',
    ])
    def test_exception_in_middleware_converted_before_prior_middleware(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(mw.log, [(404, response.content)])
        self.assertEqual(response.status_code, 404)

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.ProcessExceptionMiddleware'])
    def test_exception_in_render_passed_to_process_exception(self):
        response = self.client.get('/middleware_exceptions/exception_in_render/')
        self.assertEqual(response.content, b'Exception caught')


@override_settings(ROOT_URLCONF='middleware_exceptions.urls')
class RootUrlconfTests(SimpleTestCase):

    @override_settings(ROOT_URLCONF=None)
    def test_missing_root_urlconf(self):
        # Removing ROOT_URLCONF is safe, as override_settings will restore
        # the previously defined settings.
        del settings.ROOT_URLCONF
        with self.assertRaises(AttributeError):
            self.client.get("/middleware_exceptions/view/")


class MyMiddleware(object):

    def __init__(self, get_response=None):
        raise MiddlewareNotUsed

    def process_request(self, request):
        pass


class MyMiddlewareWithExceptionMessage(object):

    def __init__(self, get_response=None):
        raise MiddlewareNotUsed('spam eggs')

    def process_request(self, request):
        pass


@override_settings(
    DEBUG=True,
    ROOT_URLCONF='middleware_exceptions.urls',
    MIDDLEWARE=['django.middleware.common.CommonMiddleware'],
)
class MiddlewareNotUsedTests(SimpleTestCase):

    rf = RequestFactory()

    def test_raise_exception(self):
        request = self.rf.get('middleware_exceptions/view/')
        with self.assertRaises(MiddlewareNotUsed):
            MyMiddleware().process_request(request)

    @override_settings(MIDDLEWARE=['middleware_exceptions.tests.MyMiddleware'])
    def test_log(self):
        with patch_logger('django.request', 'debug') as calls:
            self.client.get('/middleware_exceptions/view/')
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            "MiddlewareNotUsed: 'middleware_exceptions.tests.MyMiddleware'"
        )

    @override_settings(MIDDLEWARE=['middleware_exceptions.tests.MyMiddlewareWithExceptionMessage'])
    def test_log_custom_message(self):
        with patch_logger('django.request', 'debug') as calls:
            self.client.get('/middleware_exceptions/view/')
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            "MiddlewareNotUsed('middleware_exceptions.tests.MyMiddlewareWithExceptionMessage'): spam eggs"
        )

    @override_settings(DEBUG=False)
    def test_do_not_log_when_debug_is_false(self):
        with patch_logger('django.request', 'debug') as calls:
            self.client.get('/middleware_exceptions/view/')
        self.assertEqual(len(calls), 0)
