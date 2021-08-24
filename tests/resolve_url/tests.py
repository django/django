from django.shortcuts import resolve_url
from django.test import SimpleTestCase, override_settings
from django.urls import NoReverseMatch, reverse_lazy

from .models import UnimportantThing
from .urls import some_view


@override_settings(ROOT_URLCONF="resolve_url.urls")
class ResolveUrlTests(SimpleTestCase):
    """
    Tests for the resolve_url() function.
    """

    def test_url_path(self):
        """
        Passing a URL path to resolve_url() results in the same url.
        """
        self.assertEqual("/something/", resolve_url("/something/"))

    def test_relative_path(self):
        """
        Passing a relative URL path to resolve_url() results in the same url.
        """
        self.assertEqual("../", resolve_url("../"))
        self.assertEqual("../relative/", resolve_url("../relative/"))
        self.assertEqual("./", resolve_url("./"))
        self.assertEqual("./relative/", resolve_url("./relative/"))

    def test_full_url(self):
        """
        Passing a full URL to resolve_url() results in the same url.
        """
        url = "http://example.com/"
        self.assertEqual(url, resolve_url(url))

    def test_model(self):
        """
        Passing a model to resolve_url() results in get_absolute_url() being
        called on that model instance.
        """
        m = UnimportantThing(importance=1)
        self.assertEqual(m.get_absolute_url(), resolve_url(m))

    def test_view_function(self):
        """
        Passing a view function to resolve_url() results in the URL path
        mapping to that view name.
        """
        resolved_url = resolve_url(some_view)
        self.assertEqual("/some-url/", resolved_url)

    def test_lazy_reverse(self):
        """
        Passing the result of reverse_lazy is resolved to a real URL
        string.
        """
        resolved_url = resolve_url(reverse_lazy("some-view"))
        self.assertIsInstance(resolved_url, str)
        self.assertEqual("/some-url/", resolved_url)

    def test_valid_view_name(self):
        """
        Passing a view name to resolve_url() results in the URL path mapping
        to that view.
        """
        resolved_url = resolve_url("some-view")
        self.assertEqual("/some-url/", resolved_url)

    def test_domain(self):
        """
        Passing a domain to resolve_url() returns the same domain.
        """
        self.assertEqual(resolve_url("example.com"), "example.com")

    def test_non_view_callable_raises_no_reverse_match(self):
        """
        Passing a non-view callable into resolve_url() raises a
        NoReverseMatch exception.
        """
        with self.assertRaises(NoReverseMatch):
            resolve_url(lambda: "asdf")
