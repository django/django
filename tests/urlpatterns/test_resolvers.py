from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls.resolvers import RegexPattern, RoutePattern, get_resolver
from django.utils.translation import gettext_lazy as _

from . import views


class RegexPatternTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(str(RegexPattern(_("^translated/$"))), "^translated/$")


class RoutePatternTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(str(RoutePattern(_("translated/"))), "translated/")

    def test_has_converters(self):
        self.assertEqual(len(RoutePattern("translated/").converters), 0)
        self.assertEqual(len(RoutePattern(_("translated/")).converters), 0)
        self.assertEqual(len(RoutePattern("translated/<int:foo>").converters), 1)
        self.assertEqual(len(RoutePattern(_("translated/<int:foo>")).converters), 1)

    def test_match_lazy_route_without_converters(self):
        pattern = RoutePattern(_("test/"))
        result = pattern.match("test/child/")
        self.assertEqual(result, ("child/", (), {}))

    def test_match_lazy_route_endpoint(self):
        pattern = RoutePattern(_("test/"), is_endpoint=True)
        result = pattern.match("test/")
        self.assertEqual(result, ("", (), {}))

    def test_match_lazy_route_with_converters(self):
        pattern = RoutePattern(_("test/<int:pk>/"))
        result = pattern.match("test/123/child/")
        self.assertEqual(result, ("child/", (), {"pk": 123}))


class ResolverCacheTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="urlpatterns.path_urls")
    def test_resolver_cache_default__root_urlconf(self):
        # resolver for a default URLconf (passing no argument) and for the
        # settings.ROOT_URLCONF is the same cached object.
        self.assertIs(get_resolver(), get_resolver("urlpatterns.path_urls"))
        self.assertIsNot(get_resolver(), get_resolver("urlpatterns.path_dynamic_urls"))


class ResolverLazyIncludeTests(SimpleTestCase):

    def test_lazy_route_resolves(self):
        resolver = get_resolver("urlpatterns.lazy_path_urls")
        for url_path, name in [
            ("/lazy/test-me/", "lazy"),
            ("/included_urls/extra/test/", "inner-extra"),
        ]:
            with self.subTest(name=name):
                match = resolver.resolve(url_path)
                self.assertEqual(match.func, views.empty_view)
                self.assertEqual(match.url_name, name)
