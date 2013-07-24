from django.conf import settings
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.core import checks
from django.db.models.loading import cache
from django.test import TestCase

from .models import (SyndicatedArticle, ExclusiveArticle, CustomArticle,
    AbstractArticle)


class SitesFrameworkTestCase(TestCase):
    def setUp(self):
        Site.objects.get_or_create(id=settings.SITE_ID,
            domain="example.com", name="example.com")
        Site.objects.create(id=settings.SITE_ID+1,
            domain="example2.com", name="example2.com")
        self._clear_app_cache()

    def tearDown(self):
        self._clear_app_cache()

    def _clear_app_cache(self):
        # If you create a model in a test, the model is accessible in other
        # tests. To avoid this, we need to clear list of all models created in
        # `sites_framework` module.
        cache.app_models['sites_framework'] = {}
        cache._get_models_cache = {}

    def test_site_fk(self):
        article = ExclusiveArticle.objects.create(title="Breaking News!",
            site_id=settings.SITE_ID)
        self.assertEqual(ExclusiveArticle.on_site.all().get(), article)

    def test_sites_m2m(self):
        article = SyndicatedArticle.objects.create(title="Fresh News!")
        article.sites.add(Site.objects.get(id=settings.SITE_ID))
        article.sites.add(Site.objects.get(id=settings.SITE_ID+1))
        article2 = SyndicatedArticle.objects.create(title="More News!")
        article2.sites.add(Site.objects.get(id=settings.SITE_ID+1))
        self.assertEqual(SyndicatedArticle.on_site.all().get(), article)

    def test_custom_named_field(self):
        article = CustomArticle.objects.create(title="Tantalizing News!",
            places_this_article_should_appear_id=settings.SITE_ID)
        self.assertEqual(CustomArticle.on_site.all().get(), article)

    def test_invalid_name(self):
        from django.db import models

        class InvalidArticle(AbstractArticle):
            site = models.ForeignKey(Site)

            objects = models.Manager()
            on_site = CurrentSiteManager("places_this_article_should_appear")

        errors = InvalidArticle.check()
        self.assertEqual(errors, [checks.Error(
            'No field InvalidArticle.places_this_article_should_appear.\n'
            'CurrentSiteManager needs a field named '
            '"places_this_article_should_appear".',
            hint='Ensure that you did not misspell the field name. '
            'Does the field exist?',
            obj=InvalidArticle.on_site)])

    def test_invalid_field_type(self):
        from django.db import models

        class ConfusedArticle(AbstractArticle):
            site = models.IntegerField()

        errors = ConfusedArticle.check()
        self.assertEqual(errors, [checks.Error(
            'CurrentSiteManager uses a non-relative field.\n'
            'ConfusedArticle.site should be a ForeignKey or ManyToManyField.',
            hint=None, obj=ConfusedArticle.on_site)])
