from django.apps import apps
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.test import TestCase, override_settings


class TestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'sitemaps'

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/testmodel/%s/' % self.id


class I18nTestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'sitemaps'

    def get_absolute_url(self):
        return reverse('i18n_testmodel', args=[self.id])


@override_settings(ROOT_URLCONF='django.contrib.sitemaps.tests.urls.http')
class SitemapTestsBase(TestCase):
    protocol = 'http'
    sites_installed = apps.is_installed('django.contrib.sites')
    domain = 'example.com' if sites_installed else 'testserver'

    def setUp(self):
        self.base_url = '%s://%s' % (self.protocol, self.domain)
        cache.clear()
        # Create an object for sitemap content.
        TestModel.objects.create(name='Test Object')
        self.i18n_model = I18nTestModel.objects.create(name='Test Object')
