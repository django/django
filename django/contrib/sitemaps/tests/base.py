from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.test import TestCase


class SitemapTestsBase(TestCase):
    protocol = 'http'
    domain = 'example.com' if Site._meta.installed else 'testserver'
    urls = 'django.contrib.sitemaps.tests.urls.http'

    def setUp(self):
        self.base_url = '%s://%s' % (self.protocol, self.domain)
        self.old_Site_meta_installed = Site._meta.installed
        cache.clear()
        # Create a user that will double as sitemap content
        User.objects.create_user('testuser', 'test@example.com', 's3krit')

    def tearDown(self):
        Site._meta.installed = self.old_Site_meta_installed
