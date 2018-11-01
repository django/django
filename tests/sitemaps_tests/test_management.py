from unittest import mock

from django.core.management import call_command

from .base import SitemapTestsBase


@mock.patch('django.contrib.sitemaps.management.commands.ping_google.ping_google')
class PingGoogleTests(SitemapTestsBase):

    def test_default(self, ping_google_func):
        call_command('ping_google')
        ping_google_func.assert_called_with(sitemap_url=None)

    def test_arg(self, ping_google_func):
        call_command('ping_google', 'foo.xml')
        ping_google_func.assert_called_with(sitemap_url='foo.xml')
