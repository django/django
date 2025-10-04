from itertools import product

from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.utils.csp import CSP
from django.views.decorators.csp import csp_override, csp_report_only_override

basic_config = {
    "default-src": [CSP.SELF],
}


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

    def test_decorator_requires_mapping(self):
        for config, decorator in product(
            [None, 0, False, [], [1, 2, 3], 42, {4, 5}],
            (csp_override, csp_report_only_override),
        ):
            with (
                self.subTest(config=config, decorator=decorator),
                self.assertRaisesMessage(TypeError, "CSP config should be a mapping"),
            ):
                decorator(config)

    def test_csp_override(self):
        @csp_override(basic_config)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertIs(hasattr(response, "_csp_ro_config"), False)

    async def test_csp_override_async_view(self):
        @csp_override(basic_config)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertIs(hasattr(response, "_csp_ro_config"), False)

    def test_csp_report_only_override(self):
        @csp_report_only_override(basic_config)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_ro_config, basic_config)
        self.assertIs(hasattr(response, "_csp_config"), False)

    async def test_csp_report_only_override_async_view(self):
        @csp_report_only_override(basic_config)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_ro_config, basic_config)
        self.assertIs(hasattr(response, "_csp_config"), False)

    def test_csp_override_both(self):
        @csp_override(basic_config)
        @csp_report_only_override(basic_config)
        def sync_view(request):
            return HttpResponse("OK")

        response = sync_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertEqual(response._csp_ro_config, basic_config)

    async def test_csp_override_both_async_view(self):
        @csp_override(basic_config)
        @csp_report_only_override(basic_config)
        async def async_view(request):
            return HttpResponse("OK")

        response = await async_view(HttpRequest())
        self.assertEqual(response._csp_config, basic_config)
        self.assertEqual(response._csp_ro_config, basic_config)
