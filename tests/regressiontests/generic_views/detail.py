from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from .models import Artist, Author, Page


class DetailViewTest(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_simple_object(self):
        res = self.client.get('/detail/obj/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], {'foo': 'bar'})
        self.assertTemplateUsed(res, 'generic_views/detail.html')

    def test_detail_by_pk(self):
        res = self.client.get('/detail/author/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_custom_pk(self):
        res = self.client.get('/detail/author/bycustompk/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_slug(self):
        res = self.client.get('/detail/author/byslug/scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(slug='scott-rosenberg'))
        self.assertEqual(res.context['author'], Author.objects.get(slug='scott-rosenberg'))
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_custom_slug(self):
        res = self.client.get('/detail/author/bycustomslug/scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(slug='scott-rosenberg'))
        self.assertEqual(res.context['author'], Author.objects.get(slug='scott-rosenberg'))
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_verbose_name(self):
        res = self.client.get('/detail/artist/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Artist.objects.get(pk=1))
        self.assertEqual(res.context['artist'], Artist.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/artist_detail.html')

    def test_template_name(self):
        res = self.client.get('/detail/author/1/template_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/about.html')

    def test_template_name_suffix(self):
        res = self.client.get('/detail/author/1/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/author_view.html')

    def test_template_name_field(self):
        res = self.client.get('/detail/page/1/field/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Page.objects.get(pk=1))
        self.assertEqual(res.context['page'], Page.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/page_template.html')

    def test_context_object_name(self):
        res = self.client.get('/detail/author/1/context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk=1))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_duplicated_context_object_name(self):
        res = self.client.get('/detail/author/1/dupe_context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')
