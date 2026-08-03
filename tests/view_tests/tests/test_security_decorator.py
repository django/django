from django.test import SimpleTestCase

from django.views.decorators.security import (
    cross_origin_embedder_policy,
)


class CrossOriginEmbedderPolicyDecoratorTests(SimpleTestCase):
    def test_valid_policies(self):
        """Valid COEP policies should not raise errors."""
        for policy in ("unsafe-none", "require-corp", "credentialless"):
            with self.subTest(policy=policy):

                @cross_origin_embedder_policy(policy)
                def view(request):
                    pass

    def test_invalid_policy_raises(self):
        """An invalid policy value raises ValueError."""
        with self.assertRaises(ValueError):
            cross_origin_embedder_policy("invalid-value")

    def test_sync_view_sets_attribute(self):
        """The decorator sets _cross_origin_embedder_policy on the
        response for synchronous views."""
        from django.http import HttpResponse

        @cross_origin_embedder_policy("require-corp")
        def my_view(request):
            return HttpResponse("OK")

        response = my_view(None)
        self.assertEqual(
            response._cross_origin_embedder_policy,
            "require-corp",
        )

    def test_async_view_sets_attribute(self):
        """The decorator sets _cross_origin_embedder_policy on the
        response for asynchronous views."""
        import asyncio

        from django.http import HttpResponse

        @cross_origin_embedder_policy("credentialless")
        async def my_async_view(request):
            return HttpResponse("OK")

        response = asyncio.run(my_async_view(None))
        self.assertEqual(
            response._cross_origin_embedder_policy,
            "credentialless",
        )

    def test_preserves_function_metadata(self):
        """The decorator preserves the wrapped function's metadata."""
        from django.http import HttpResponse

        @cross_origin_embedder_policy("require-corp")
        def my_named_view(request):
            """My docstring."""
            return HttpResponse("OK")

        self.assertEqual(my_named_view.__name__, "my_named_view")
        self.assertEqual(my_named_view.__doc__, "My docstring.")
