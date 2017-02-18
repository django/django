from django.apps import apps
from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core import checks
from django.db import models
from django.test import TestCase

from .models import (
    AbstractArticle, CustomArticle, ExclusiveArticle, SyndicatedArticle,
)


class SitesFrameworkTestCase(TestCase):
    def setUp(self):
        Site.objects.get_or_create(id=settings.SITE_ID, domain="example.com", name="example.com")
        Site.objects.create(id=settings.SITE_ID + 1, domain="example2.com", name="example2.com")

        self._old_models = apps.app_configs['sites_framework'].models.copy()

    def tearDown(self):
        apps.app_configs['sites_framework'].models = self._old_models
        apps.all_models['sites_framework'] = self._old_models
        apps.clear_cache()

    def test_site_fk(self):
        article = ExclusiveArticle.objects.create(title="Breaking News!", site_id=settings.SITE_ID)
        self.assertEqual(ExclusiveArticle.on_site.all().get(), article)

    def test_sites_m2m(self):
        article = SyndicatedArticle.objects.create(title="Fresh News!")
        article.sites.add(Site.objects.get(id=settings.SITE_ID))
        article.sites.add(Site.objects.get(id=settings.SITE_ID + 1))
        article2 = SyndicatedArticle.objects.create(title="More News!")
        article2.sites.add(Site.objects.get(id=settings.SITE_ID + 1))
        self.assertEqual(SyndicatedArticle.on_site.all().get(), article)

    def test_custom_named_field(self):
        article = CustomArticle.objects.create(title="Tantalizing News!", places_this_article_should_appear_id=settings.SITE_ID)
        self.assertEqual(CustomArticle.on_site.all().get(), article)

    def test_invalid_name(self):

        class InvalidArticle(AbstractArticle):
            site = models.ForeignKey(Site)

            objects = models.Manager()
            on_site = CurrentSiteManager("places_this_article_should_appear")

        errors = InvalidArticle.check()
        expected = [
            checks.Error(
                ("CurrentSiteManager could not find a field named "
                 "'places_this_article_should_appear'."),
                hint=None,
                obj=InvalidArticle.on_site,
                id='sites.E001',
            )
        ]
        self.assertEqual(errors, expected)

    def test_invalid_field_type(self):

        class ConfusedArticle(AbstractArticle):
            site = models.IntegerField()

        errors = ConfusedArticle.check()
        expected = [
            checks.Error(
                "CurrentSiteManager cannot use 'ConfusedArticle.site' as it is not a ForeignKey or ManyToManyField.",
                hint=None,
                obj=ConfusedArticle.on_site,
                id='sites.E002',
            )
        ]
        self.assertEqual(errors, expected)
