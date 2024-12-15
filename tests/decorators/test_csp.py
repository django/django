from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.middleware import csp
from django.test import SimpleTestCase
from django.views.decorators.csp import csp_exempt, csp_override

basic_config = {
    "DIRECTIVES": {
        "default-src": [csp.SELF],
    }
}


class CSPExemptDecoratorTest(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = csp_exempt()(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = csp_exempt()(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_csp_exempt_both(self):
        @csp_exempt
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertTrue(response._csp_exempt)
        self.assertTrue(response._csp_exempt_ro)

    async def test_csp_exempt_both_async_view(self):
        @csp_exempt
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertTrue(response._csp_exempt)
        self.assertTrue(response._csp_exempt_ro)

    def test_csp_exempt_enforced(self):
        @csp_exempt(report_only=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertTrue(response._csp_exempt)
        self.assertIsNone(getattr(response, "_csp_exempt_ro", None))

    async def test_csp_exempt_enforced_async_view(self):
        @csp_exempt(report_only=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertTrue(response._csp_exempt)
        self.assertIsNone(getattr(response, "_csp_exempt_ro", None))

    def test_csp_exempt_report_only(self):
        @csp_exempt(enforced=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_exempt", None))
        self.assertTrue(response._csp_exempt_ro)

    async def test_csp_exempt_report_only_async_view(self):
        @csp_exempt(enforced=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_exempt", None))
        self.assertTrue(response._csp_exempt_ro)

    def test_csp_exempt_neither(self):
        @csp_exempt(enforced=False, report_only=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_exempt", None))
        self.assertIsNone(getattr(response, "_csp_exempt_ro", None))

    async def test_csp_exempt_neither_async_view(self):
        @csp_exempt(enforced=False, report_only=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_exempt", None))
        self.assertIsNone(getattr(response, "_csp_exempt_ro", None))


class CSPOverrideDecoratorTest(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = csp_override({})(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = csp_override({})(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_csp_override_both(self):
        @csp_override(basic_config)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertEqual(response._csp_config_ro, basic_config)

    async def test_csp_override_both_async_view(self):
        @csp_override(basic_config)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertEqual(response._csp_config_ro, basic_config)

    def test_csp_override_enforced(self):
        @csp_override(basic_config, report_only=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertIsNone(getattr(response, "_csp_config_ro", None))

    async def test_csp_override_enforced_async_view(self):
        @csp_override(basic_config, report_only=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertIsNone(getattr(response, "_csp_config_ro", None))

    def test_csp_override_report_only(self):
        @csp_override(basic_config, enforced=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_config_ro, basic_config)
        self.assertIsNone(getattr(response, "_csp_config", None))

    async def test_csp_override_report_only_async_view(self):
        @csp_override(basic_config, enforced=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_config_ro, basic_config)
        self.assertIsNone(getattr(response, "_csp_config", None))

    def test_csp_override_neither(self):
        @csp_override(basic_config, enforced=False, report_only=False)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_config", None))
        self.assertIsNone(getattr(response, "_csp_config_ro", None))

    async def test_csp_override_neither_async_view(self):
        @csp_override(basic_config, enforced=False, report_only=False)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertIsNone(getattr(response, "_csp_config", None))
        self.assertIsNone(getattr(response, "_csp_config_ro", None))
