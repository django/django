from thibaud.apps import apps
from thibaud.contrib.sites.models import Site
from thibaud.test import TestCase
from thibaud.test.utils import modify_settings, override_settings


@override_settings(
    ROOT_URLCONF="flatpages_tests.urls",
    SITE_ID=1,
)
@modify_settings(
    INSTALLED_APPS={
        "append": ["thibaud.contrib.sitemaps", "thibaud.contrib.flatpages"],
    },
)
class FlatpagesSitemapTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This cleanup is necessary because contrib.sites cache
        # makes tests interfere with each other, see #11505
        Site.objects.clear_cache()

    @classmethod
    def setUpTestData(cls):
        Site = apps.get_model("sites.Site")
        current_site = Site.objects.get_current()
        current_site.flatpage_set.create(url="/foo/", title="foo")
        current_site.flatpage_set.create(
            url="/private-foo/", title="private foo", registration_required=True
        )

    def test_flatpage_sitemap(self):
        response = self.client.get("/flatpages/sitemap.xml")
        self.assertIn(
            b"<url><loc>http://example.com/flatpage_root/foo/</loc></url>",
            response.getvalue(),
        )
        self.assertNotIn(
            b"<url><loc>http://example.com/flatpage_root/private-foo/</loc></url>",
            response.getvalue(),
        )
