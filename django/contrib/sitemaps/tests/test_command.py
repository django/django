from __future__ import unicode_literals

from django.contrib.sitemaps import _get_sitemap_url

from .base import SitemapTestsBase


class PingGoogleTests(SitemapTestsBase):
    """
    Test the function used to generate the URL sent to Google as site map.
    """
    def test_https(self):
        kwargs = {}
        url = _get_sitemap_url(**kwargs)
        self.assertEqual(url, 'http://example.com/simple/custom-index.xml')

        kwargs = {
            'sitemap_url': None,
            'site_domain': None,
            'is_secure': True,
        }
        url = _get_sitemap_url(**kwargs)
        self.assertEqual(url, 'https://example.com/simple/custom-index.xml')

    def test_domain_override(self):
        kwargs = {
            'sitemap_url': None,
            'site_domain': 'djangosite.com',
            'is_secure': False,
        }
        url = _get_sitemap_url(**kwargs)
        self.assertEqual(url, 'http://djangosite.com/simple/custom-index.xml')

    def test_path_override(self):
        kwargs = {
            'sitemap_url': '/sitemap.xml',
            'site_domain': None,
            'is_secure': False,
        }
        url = _get_sitemap_url(**kwargs)
        self.assertEqual(url, 'http://example.com/sitemap.xml')
