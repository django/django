from __future__ import unicode_literals

from django.apps import apps
from django.test import TestCase
from django.test.utils import modify_settings, override_settings


@override_settings(
    ROOT_URLCONF='django.contrib.flatpages.tests.urls',
    SITE_ID=1,
)
@modify_settings(INSTALLED_APPS={'append': ['django.contrib.sitemaps']},)
class FlatpagesSitemapTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Site = apps.get_model('sites.Site')
        current_site = Site.objects.get_current()
        current_site.flatpage_set.create(url="/foo/", title="foo")
        current_site.flatpage_set.create(url="/private-foo/", title="private foo", registration_required=True)

    def test_flatpage_sitemap(self):
        response = self.client.get('/flatpages/sitemap.xml')
        self.assertIn(b'<url><loc>http://example.com/foo/</loc></url>', response.getvalue())
        self.assertNotIn(b'<url><loc>http://example.com/private-foo/</loc></url>', response.getvalue())
