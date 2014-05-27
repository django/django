from freedom.apps import apps
from freedom.core.cache import cache
from freedom.db import models
from freedom.test import TestCase, override_settings


class TestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'sitemaps'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/testmodel/%s/' % self.id


@override_settings(ROOT_URLCONF='freedom.contrib.sitemaps.tests.urls.http')
class SitemapTestsBase(TestCase):
    protocol = 'http'
    sites_installed = apps.is_installed('freedom.contrib.sites')
    domain = 'example.com' if sites_installed else 'testserver'

    def setUp(self):
        self.base_url = '%s://%s' % (self.protocol, self.domain)
        cache.clear()
        # Create an object for sitemap content.
        TestModel.objects.create(name='Test Object')
