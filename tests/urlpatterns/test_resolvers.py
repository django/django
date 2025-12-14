from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import include, path, resolve
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


class LazyRouteIncludeTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF=__name__)
    def test_lazy_route_with_include_resolves(self):
        match = resolve("/test/child/")
        self.assertEqual(match.url_name, "child")
