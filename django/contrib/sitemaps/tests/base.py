from django.apps import apps
from django.core.cache import cache
from django.db import models
from django.test import TestCase


class TestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'sitemaps'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/testmodel/%s/' % self.id


class SitemapTestsBase(TestCase):
    protocol = 'http'
    sites_installed = apps.is_installed('django.contrib.sites')
    domain = 'example.com' if sites_installed else 'testserver'
    urls = 'django.contrib.sitemaps.tests.urls.http'

    def setUp(self):
        self.base_url = '%s://%s' % (self.protocol, self.domain)
        cache.clear()
        # Create an object for sitemap content.
        TestModel.objects.create(name='Test Object')
