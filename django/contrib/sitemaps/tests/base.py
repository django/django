from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import models
from django.test import TestCase


class TestModel(models.Model):
    "A test model for "
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'sitemaps'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/testmodel/%s/' % self.id


class SitemapTestsBase(TestCase):
    protocol = 'http'
    domain = 'example.com' if Site._meta.installed else 'testserver'
    urls = 'django.contrib.sitemaps.tests.urls.http'

    def setUp(self):
        self.base_url = '%s://%s' % (self.protocol, self.domain)
        self.old_Site_meta_installed = Site._meta.installed
        cache.clear()
        # Create an object for sitemap content.
        TestModel.objects.create(name='Test Object')

    def tearDown(self):
        Site._meta.installed = self.old_Site_meta_installed
