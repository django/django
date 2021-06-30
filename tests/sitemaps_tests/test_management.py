from unittest import mock

from mango.core.management import call_command

from .base import SitemapTestsBase


@mock.patch('mango.contrib.sitemaps.management.commands.ping_google.ping_google')
class PingGoogleTests(SitemapTestsBase):

    def test_default(self, ping_google_func):
        call_command('ping_google')
        ping_google_func.assert_called_with(sitemap_url=None, sitemap_uses_https=True)

    def test_args(self, ping_google_func):
        call_command('ping_google', 'foo.xml', '--sitemap-uses-http')
        ping_google_func.assert_called_with(sitemap_url='foo.xml', sitemap_uses_https=False)
