from django.contrib.sitemaps import (
    SitemapNotFound, _get_sitemap_full_url, ping_google,
)
from django.core.exceptions import ImproperlyConfigured
from django.test import mock, modify_settings, override_settings
from django.utils.six.moves.urllib.parse import urlencode

from .base import SitemapTestsBase


class PingGoogleTests(SitemapTestsBase):

    @mock.patch('django.contrib.sitemaps.urlopen')
    def test_something(self, urlopen):
        ping_google()
        params = urlencode({'sitemap': 'http://example.com/sitemap-without-entries/sitemap.xml'})
        full_url = 'https://www.google.com/webmasters/tools/ping?%s' % params
        urlopen.assert_called_with(full_url)

    def test_get_sitemap_full_url_global(self):
        self.assertEqual(_get_sitemap_full_url(None), 'http://example.com/sitemap-without-entries/sitemap.xml')

    @override_settings(ROOT_URLCONF='sitemaps_tests.urls.index_only')
    def test_get_sitemap_full_url_index(self):
        self.assertEqual(_get_sitemap_full_url(None), 'http://example.com/simple/index.xml')

    @override_settings(ROOT_URLCONF='sitemaps_tests.urls.empty')
    def test_get_sitemap_full_url_not_detected(self):
        msg = "You didn't provide a sitemap_url, and the sitemap URL couldn't be auto-detected."
        with self.assertRaisesMessage(SitemapNotFound, msg):
            _get_sitemap_full_url(None)

    def test_get_sitemap_full_url_exact_url(self):
        self.assertEqual(_get_sitemap_full_url('/foo.xml'), 'http://example.com/foo.xml')

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_get_sitemap_full_url_no_sites(self):
        msg = "ping_google requires django.contrib.sites, which isn't installed."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            _get_sitemap_full_url(None)
