from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import get_resolver, resolve
from django.urls.resolvers import RegexPattern, RoutePattern
from django.utils.translation import gettext_lazy as _


class RegexPatternTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(str(RegexPattern(_("^translated/$"))), "^translated/$")


class ResolverCacheTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="urlpatterns.path_urls")
    def test_resolver_cache_default__root_urlconf(self):
        # resolver for a default URLconf (passing no argument) and for the
        # settings.ROOT_URLCONF is the same cached object.
        self.assertIs(get_resolver(), get_resolver("urlpatterns.path_urls"))
        self.assertIsNot(get_resolver(), get_resolver("urlpatterns.path_dynamic_urls"))


class LazyRouteIncludeTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="urlpatterns.path_urls")
    def test_lazy_route_with_include_resolves(self):
        match = resolve("/lazy/child/")
        self.assertEqual(match.url_name, "child")


class RoutePatternEndpointMatchTests(SimpleTestCase):
    def test_match_endpoint_with_lazy_route(self):
        pattern = RoutePattern("test/")
        result = pattern.match("test/")
        self.assertEqual(
            result,
            ("", (), {}),
        )


class RoutePatternTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(str(RoutePattern(_("translated/"))), "translated/")

    def test_has_converters(self):
        self.assertEqual(len(RoutePattern("translated/").converters), 0)
        self.assertEqual(len(RoutePattern(_("translated/")).converters), 0)
        self.assertEqual(len(RoutePattern("translated/<int:foo>").converters), 1)
        self.assertEqual(len(RoutePattern(_("translated/<int:foo>")).converters), 1)
