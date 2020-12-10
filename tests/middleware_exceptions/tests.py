from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

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

    @override_settings(MIDDLEWARE=['middleware_exceptions.middleware.NoTemplateResponseMiddleware'])
    def test_process_template_response_returns_none(self):
        msg = (
            "NoTemplateResponseMiddleware.process_template_response didn't "
            "return an HttpResponse object. It returned None instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.client.get('/middleware_exceptions/template_response/')

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
        'middleware_exceptions.middleware.ProcessExceptionMiddleware',
        'middleware_exceptions.middleware.ProcessExceptionLogMiddleware',
    ])
    def test_response_from_process_exception_when_return_response(self):
        response = self.client.get('/middleware_exceptions/error/')
        self.assertEqual(mw.log, ['process-exception'])
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


class MyMiddleware:

    def __init__(self, get_response):
        raise MiddlewareNotUsed

    def process_request(self, request):
        pass


class MyMiddlewareWithExceptionMessage:

    def __init__(self, get_response):
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
            MyMiddleware(lambda req: HttpResponse()).process_request(request)

    @override_settings(MIDDLEWARE=['middleware_exceptions.tests.MyMiddleware'])
    def test_log(self):
        with self.assertLogs('django.request', 'DEBUG') as cm:
            self.client.get('/middleware_exceptions/view/')
        self.assertEqual(
            cm.records[0].getMessage(),
            "MiddlewareNotUsed: 'middleware_exceptions.tests.MyMiddleware'"
        )

    @override_settings(MIDDLEWARE=['middleware_exceptions.tests.MyMiddlewareWithExceptionMessage'])
    def test_log_custom_message(self):
        with self.assertLogs('django.request', 'DEBUG') as cm:
            self.client.get('/middleware_exceptions/view/')
        self.assertEqual(
            cm.records[0].getMessage(),
            "MiddlewareNotUsed('middleware_exceptions.tests.MyMiddlewareWithExceptionMessage'): spam eggs"
        )

    @override_settings(
        DEBUG=False,
        MIDDLEWARE=['middleware_exceptions.tests.MyMiddleware'],
    )
    def test_do_not_log_when_debug_is_false(self):
        with self.assertRaisesMessage(AssertionError, 'no logs'):
            with self.assertLogs('django.request', 'DEBUG'):
                self.client.get('/middleware_exceptions/view/')


@override_settings(
    DEBUG=True,
    ROOT_URLCONF='middleware_exceptions.urls',
)
class MiddlewareSyncAsyncTests(SimpleTestCase):
    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.PaymentMiddleware',
    ])
    def test_sync_middleware(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.status_code, 402)

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.DecoratedPaymentMiddleware',
    ])
    def test_sync_decorated_middleware(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.status_code, 402)

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.async_payment_middleware',
    ])
    def test_async_middleware(self):
        with self.assertLogs('django.request', 'DEBUG') as cm:
            response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(
            cm.records[0].getMessage(),
            "Synchronous middleware "
            "middleware_exceptions.middleware.async_payment_middleware "
            "adapted.",
        )

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.NotSyncOrAsyncMiddleware',
    ])
    def test_not_sync_or_async_middleware(self):
        msg = (
            'Middleware '
            'middleware_exceptions.middleware.NotSyncOrAsyncMiddleware must '
            'have at least one of sync_capable/async_capable set to True.'
        )
        with self.assertRaisesMessage(RuntimeError, msg):
            self.client.get('/middleware_exceptions/view/')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.PaymentMiddleware',
    ])
    async def test_sync_middleware_async(self):
        with self.assertLogs('django.request', 'DEBUG') as cm:
            response = await self.async_client.get('/middleware_exceptions/view/')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(
            cm.records[0].getMessage(),
            "Asynchronous middleware "
            "middleware_exceptions.middleware.PaymentMiddleware adapted.",
        )

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.async_payment_middleware',
    ])
    async def test_async_middleware_async(self):
        with self.assertLogs('django.request', 'WARNING') as cm:
            response = await self.async_client.get('/middleware_exceptions/view/')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(
            cm.records[0].getMessage(),
            'Payment Required: /middleware_exceptions/view/',
        )

    @override_settings(
        DEBUG=False,
        MIDDLEWARE=[
            'middleware_exceptions.middleware.AsyncNoTemplateResponseMiddleware',
        ],
    )
    def test_async_process_template_response_returns_none_with_sync_client(self):
        msg = (
            "AsyncNoTemplateResponseMiddleware.process_template_response "
            "didn't return an HttpResponse object."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.client.get('/middleware_exceptions/template_response/')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.SyncAndAsyncMiddleware',
    ])
    async def test_async_and_sync_middleware_async_call(self):
        response = await self.async_client.get('/middleware_exceptions/view/')
        self.assertEqual(response.content, b'OK')
        self.assertEqual(response.status_code, 200)

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.SyncAndAsyncMiddleware',
    ])
    def test_async_and_sync_middleware_sync_call(self):
        response = self.client.get('/middleware_exceptions/view/')
        self.assertEqual(response.content, b'OK')
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF='middleware_exceptions.urls')
class AsyncMiddlewareTests(SimpleTestCase):
    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncTemplateResponseMiddleware',
    ])
    async def test_process_template_response(self):
        response = await self.async_client.get(
            '/middleware_exceptions/template_response/'
        )
        self.assertEqual(
            response.content,
            b'template_response OK\nAsyncTemplateResponseMiddleware',
        )

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncNoTemplateResponseMiddleware',
    ])
    async def test_process_template_response_returns_none(self):
        msg = (
            "AsyncNoTemplateResponseMiddleware.process_template_response "
            "didn't return an HttpResponse object. It returned None instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            await self.async_client.get('/middleware_exceptions/template_response/')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncProcessExceptionMiddleware',
    ])
    async def test_exception_in_render_passed_to_process_exception(self):
        response = await self.async_client.get(
            '/middleware_exceptions/exception_in_render/'
        )
        self.assertEqual(response.content, b'Exception caught')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncProcessExceptionMiddleware',
    ])
    async def test_exception_in_async_render_passed_to_process_exception(self):
        response = await self.async_client.get(
            '/middleware_exceptions/async_exception_in_render/'
        )
        self.assertEqual(response.content, b'Exception caught')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncProcessExceptionMiddleware',
    ])
    async def test_view_exception_handled_by_process_exception(self):
        response = await self.async_client.get('/middleware_exceptions/error/')
        self.assertEqual(response.content, b'Exception caught')

    @override_settings(MIDDLEWARE=[
        'middleware_exceptions.middleware.AsyncProcessViewMiddleware',
    ])
    async def test_process_view_return_response(self):
        response = await self.async_client.get('/middleware_exceptions/view/')
        self.assertEqual(response.content, b'Processed view normal_view')
