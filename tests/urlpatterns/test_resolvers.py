from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import get_resolver, include, path, resolve
from django.urls.resolvers import RegexPattern
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    path(
        _("test/"),
        include(
            [
                path("child/", lambda request: None, name="child"),
            ]
        ),
    ),
]


class RegexPatternTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(
            str(RegexPattern(_("^translated/$"))),
            "^translated/$",
        )


class ResolverCacheTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="urlpatterns.path_urls")
    def test_resolver_cache_default__root_urlconf(self):
        # Resolver for the default URLconf (no argument) and for
        # settings.ROOT_URLCONF should be the same cached object.
        self.assertIs(
            get_resolver(),
            get_resolver("urlpatterns.path_urls"),
        )
        self.assertIsNot(
            get_resolver(),
            get_resolver("urlpatterns.path_dynamic_urls"),
        )


class LazyRouteIncludeTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF=__name__)
    def test_lazy_route_with_include_resolves(self):
        match = resolve("/test/child/")
        self.assertEqual(match.url_name, "child")
