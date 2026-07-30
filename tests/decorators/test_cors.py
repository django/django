from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.views.decorators.cors import cross_origin_resource_policy


class CrossOriginResourcePolicyDecoratorTests(SimpleTestCase):
    request = RequestFactory()

    def test_valid_values(self):
        """The decorator accepts all valid CORP values."""
        for policy in ("same-origin", "same-site", "cross-origin"):
            with self.subTest(policy=policy):

                @cross_origin_resource_policy(policy)
                def view(request):
                    return HttpResponse()

                response = view(self.request.get("/"))
                self.assertEqual(response._cross_origin_resource_policy, policy)

    def test_invalid_value_raises(self):
        """The decorator raises ValueError for invalid policy values."""
        with self.assertRaises(ValueError):
            cross_origin_resource_policy("invalid-value")

    def test_async_view(self):
        """The decorator wraps async views correctly."""
        import asyncio

        @cross_origin_resource_policy("cross-origin")
        async def async_view(request):
            return HttpResponse()

        response = asyncio.run(async_view(self.request.get("/")))
        self.assertEqual(response._cross_origin_resource_policy, "cross-origin")

    def test_preserves_view_metadata(self):
        """The decorator preserves the wrapped view's metadata."""

        def my_view(request):
            """My view docstring."""
            return HttpResponse()

        decorated = cross_origin_resource_policy("same-origin")(my_view)
        self.assertEqual(decorated.__name__, "my_view")
        self.assertEqual(decorated.__doc__, "My view docstring.")
