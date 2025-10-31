from django.conf import settings
from django.contrib.sites.context_processors import site
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core import checks
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.client import RequestFactory
from django.test.utils import isolate_apps

from .models import CustomArticle, ExclusiveArticle, SyndicatedArticle


class SitesFrameworkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Site.objects.get_or_create(
            id=settings.SITE_ID, domain="example.com", name="example.com"
        )
        Site.objects.create(
            id=settings.SITE_ID + 1, domain="example2.com", name="example2.com"
        )

    def test_site_fk(self):
        article = ExclusiveArticle.objects.create(
            title="Breaking News!", site_id=settings.SITE_ID
        )
        self.assertEqual(ExclusiveArticle.on_site.get(), article)

    def test_sites_m2m(self):
        article = SyndicatedArticle.objects.create(title="Fresh News!")
        article.sites.add(Site.objects.get(id=settings.SITE_ID))
        article.sites.add(Site.objects.get(id=settings.SITE_ID + 1))
        article2 = SyndicatedArticle.objects.create(title="More News!")
        article2.sites.add(Site.objects.get(id=settings.SITE_ID + 1))
        self.assertEqual(SyndicatedArticle.on_site.get(), article)

    def test_custom_named_field(self):
        article = CustomArticle.objects.create(
            title="Tantalizing News!",
            places_this_article_should_appear_id=settings.SITE_ID,
        )
        self.assertEqual(CustomArticle.on_site.get(), article)


@isolate_apps("sites_framework")
class CurrentSiteManagerChecksTests(SimpleTestCase):
    def test_invalid_name(self):
        class InvalidArticle(models.Model):
            on_site = CurrentSiteManager("places_this_article_should_appear")

        errors = InvalidArticle.check()
        expected = [
            checks.Error(
                "CurrentSiteManager could not find a field named "
                "'places_this_article_should_appear'.",
                obj=InvalidArticle.on_site,
                id="sites.E001",
            )
        ]
        self.assertEqual(errors, expected)

    def test_invalid_field_type(self):
        class ConfusedArticle(models.Model):
            site = models.IntegerField()
            on_site = CurrentSiteManager()

        errors = ConfusedArticle.check()
        expected = [
            checks.Error(
                "CurrentSiteManager cannot use 'ConfusedArticle.site' as it is "
                "not a foreign key or a many-to-many field.",
                obj=ConfusedArticle.on_site,
                id="sites.E002",
            )
        ]
        self.assertEqual(errors, expected)


class ContextProcessorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_context_processor(self):
        site_obj = Site.objects.get_current()
        request = self.factory.get("/")
        context = site(request)
        self.assertIn("site", context)
        self.assertEqual(context["site"].name, site_obj.name)
        self.assertEqual(context["site"].domain, site_obj.domain)

    def test_context_processor_without_sites_framework(self):
        server_url = "testserver"
        apps = list(settings.INSTALLED_APPS)
        apps.remove("django.contrib.sites")
        with self.settings(INSTALLED_APPS=apps):
            request = self.factory.get("/")
            context = site(request)

        self.assertEqual(context["site"].name, server_url)
        self.assertEqual(context["site"].domain, server_url)
