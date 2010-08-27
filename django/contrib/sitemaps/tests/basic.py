from datetime import date
from django.conf import settings
from django.test import TestCase
from django.utils.formats import localize
from django.utils.translation import activate


class SitemapTests(TestCase):
    urls = 'django.contrib.sitemaps.tests.urls'

    def setUp(self):
        self.old_USE_L10N = settings.USE_L10N

    def tearDown(self):
        settings.USE_L10N = self.old_USE_L10N

    def test_simple_sitemap(self):
        "A simple sitemap can be rendered"
        # Retrieve the sitemap.
        response = self.client.get('/sitemaps/sitemap.xml')
        # Check for all the important bits:
        self.assertEquals(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://example.com/ticket14164</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.5</priority></url>
</urlset>
""" % date.today().strftime('%Y-%m-%d'))

    def test_localized_priority(self):
        "The priority value should not be localized (Refs #14164)"
        # Localization should be active
        settings.USE_L10N = True
        activate('fr')
        self.assertEqual(u'0,3', localize(0.3))

        # Retrieve the sitemap. Check that priorities
        # haven't been rendered in localized format
        response = self.client.get('/sitemaps/sitemap.xml')
        self.assertContains(response, '<priority>0.5</priority>')
        self.assertContains(response, '<lastmod>%s</lastmod>' % date.today().strftime('%Y-%m-%d'))
