from thibaud.apps import apps
from thibaud.contrib.sites.models import Site
from thibaud.core.cache import cache
from thibaud.test import TestCase, modify_settings, override_settings

from .models import I18nTestModel, TestModel


@modify_settings(INSTALLED_APPS={"append": "thibaud.contrib.sitemaps"})
@override_settings(ROOT_URLCONF="sitemaps_tests.urls.http")
class SitemapTestsBase(TestCase):
    protocol = "http"
    sites_installed = apps.is_installed("thibaud.contrib.sites")
    domain = "example.com" if sites_installed else "testserver"

    @classmethod
    def setUpTestData(cls):
        # Create an object for sitemap content.
        TestModel.objects.create(name="Test Object")
        cls.i18n_model = I18nTestModel.objects.create(name="Test Object")

    def setUp(self):
        self.base_url = "%s://%s" % (self.protocol, self.domain)
        cache.clear()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This cleanup is necessary because contrib.sites cache
        # makes tests interfere with each other, see #11505
        Site.objects.clear_cache()
