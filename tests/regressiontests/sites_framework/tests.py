from __future__ import absolute_import

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase

from .models import (SyndicatedArticle, ExclusiveArticle, CustomArticle,
    InvalidArticle, ConfusedArticle)


class SitesFrameworkTestCase(TestCase):
    def setUp(self):
        Site.objects.get_or_create(id=settings.SITE_ID, domain="example.com", name="example.com")
        Site.objects.create(id=settings.SITE_ID+1, domain="example2.com", name="example2.com")

    def test_site_fk(self):
        article = ExclusiveArticle.objects.create(title="Breaking News!", site_id=settings.SITE_ID)
        self.assertEqual(ExclusiveArticle.on_site.all().get(), article)

    def test_sites_m2m(self):
        article = SyndicatedArticle.objects.create(title="Fresh News!")
        article.sites.add(Site.objects.get(id=settings.SITE_ID))
        article.sites.add(Site.objects.get(id=settings.SITE_ID+1))
        article2 = SyndicatedArticle.objects.create(title="More News!")
        article2.sites.add(Site.objects.get(id=settings.SITE_ID+1))
        self.assertEqual(SyndicatedArticle.on_site.all().get(), article)

    def test_custom_named_field(self):
        article = CustomArticle.objects.create(title="Tantalizing News!", places_this_article_should_appear_id=settings.SITE_ID)
        self.assertEqual(CustomArticle.on_site.all().get(), article)

    def test_invalid_name(self):
        article = InvalidArticle.objects.create(title="Bad News!", site_id=settings.SITE_ID)
        self.assertRaises(ValueError, InvalidArticle.on_site.all)

    def test_invalid_field_type(self):
        article = ConfusedArticle.objects.create(title="More Bad News!", site=settings.SITE_ID)
        self.assertRaises(TypeError, ConfusedArticle.on_site.all)
