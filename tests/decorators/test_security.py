from inspect import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase, override_settings
from django.views.decorators.security import (
    cross_origin_embedder_policy,
    cross_origin_resource_policy,
)


class CrossOriginEmbedderPolicyDecoratorTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = cross_origin_embedder_policy("require-corp")(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = cross_origin_embedder_policy("require-corp")(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_valid_policies(self):
        for policy in ("unsafe-none", "require-corp", "credentialless"):
            with self.subTest(policy=policy):

                @cross_origin_embedder_policy(policy)
                def view(request):
                    pass

    def test_invalid_policy_raises(self):
        msg = (
            "Invalid Cross-Origin-Embedder-Policy value 'invalid-value'. "
            "Valid values are: credentialless, require-corp, unsafe-none."
        )
        with self.assertRaisesMessage(ValueError, msg):
            cross_origin_embedder_policy("invalid-value")

    def test_sync_view_sets_attribute(self):
        @cross_origin_embedder_policy("require-corp")
        def my_view(request):
            return HttpResponse("OK")

        response = my_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_embedder_policy,
            "require-corp",
        )

    async def test_async_view_sets_attribute(self):
        @cross_origin_embedder_policy("credentialless")
        async def my_async_view(request):
            return HttpResponse("OK")

        response = await my_async_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_embedder_policy,
            "credentialless",
        )

    def test_preserves_function_metadata(self):
        @cross_origin_embedder_policy("require-corp")
        def my_named_view(request):
            """My docstring."""
            return HttpResponse("OK")

        self.assertEqual(my_named_view.__name__, "my_named_view")
        self.assertEqual(my_named_view.__doc__, "My docstring.")

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_CROSS_ORIGIN_EMBEDDER_POLICY="require-corp",
    )
    def test_decorator_overrides_restrictive_global(self):
        @cross_origin_embedder_policy("unsafe-none")
        def my_view(request):
            return HttpResponse("OK")

        response = my_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_embedder_policy,
            "unsafe-none",
        )


class CrossOriginResourcePolicyDecoratorTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = cross_origin_resource_policy("same-origin")(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = cross_origin_resource_policy("same-origin")(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_valid_policies(self):
        for policy in ("same-origin", "same-site", "cross-origin"):
            with self.subTest(policy=policy):

                @cross_origin_resource_policy(policy)
                def view(request):
                    pass

    def test_invalid_policy_raises(self):
        msg = (
            "Invalid Cross-Origin-Resource-Policy value 'invalid-value'. "
            "Valid values are: cross-origin, same-origin, same-site."
        )
        with self.assertRaisesMessage(ValueError, msg):
            cross_origin_resource_policy("invalid-value")

    def test_sync_view_sets_attribute(self):
        @cross_origin_resource_policy("cross-origin")
        def my_view(request):
            return HttpResponse("OK")

        response = my_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_resource_policy,
            "cross-origin",
        )

    async def test_async_view_sets_attribute(self):
        @cross_origin_resource_policy("same-site")
        async def my_async_view(request):
            return HttpResponse("OK")

        response = await my_async_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_resource_policy,
            "same-site",
        )

    def test_preserves_function_metadata(self):
        @cross_origin_resource_policy("same-origin")
        def my_named_view(request):
            """My docstring."""
            return HttpResponse("OK")

        self.assertEqual(my_named_view.__name__, "my_named_view")
        self.assertEqual(my_named_view.__doc__, "My docstring.")

    @override_settings(
        MIDDLEWARE=["django.middleware.security.SecurityMiddleware"],
        SECURE_CROSS_ORIGIN_RESOURCE_POLICY="same-origin",
    )
    def test_decorator_overrides_restrictive_global(self):
        @cross_origin_resource_policy("cross-origin")
        def my_view(request):
            return HttpResponse("OK")

        response = my_view(HttpRequest())
        self.assertEqual(
            response._cross_origin_resource_policy,
            "cross-origin",
        )
