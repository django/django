from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import TestCase, override_settings
from django.views.generic.base import View

from .models import Artist, Author, Page


@override_settings(ROOT_URLCONF='generic_views.urls')
class DetailViewTest(TestCase):
    fixtures = ['generic-views-test-data.json']

    def test_simple_object(self):
        res = self.client.get('/detail/obj/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], {'foo': 'bar'})
        self.assertIsInstance(res.context['view'], View)
        self.assertTemplateUsed(res, 'generic_views/detail.html')

    def test_detail_by_pk(self):
        res = self.client.get('/detail/author/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_missing_object(self):
        res = self.client.get('/detail/author/500/')
        self.assertEqual(res.status_code, 404)

    def test_detail_object_does_not_exist(self):
        self.assertRaises(ObjectDoesNotExist, self.client.get, '/detail/doesnotexist/1/')

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

    def test_detail_by_pk_ignore_slug(self):
        author = Author.objects.get(pk=1)
        res = self.client.get('/detail/author/bypkignoreslug/1-roberto-bolano/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], author)
        self.assertEqual(res.context['author'], author)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_ignore_slug_mismatch(self):
        author = Author.objects.get(pk=1)
        res = self.client.get('/detail/author/bypkignoreslug/1-scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], author)
        self.assertEqual(res.context['author'], author)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_and_slug(self):
        author = Author.objects.get(pk=1)
        res = self.client.get('/detail/author/bypkandslug/1-roberto-bolano/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], author)
        self.assertEqual(res.context['author'], author)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_and_slug_mismatch_404(self):
        res = self.client.get('/detail/author/bypkandslug/1-scott-rosenberg/')
        self.assertEqual(res.status_code, 404)

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
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_duplicated_context_object_name(self):
        res = self.client.get('/detail/author/1/dupe_context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')

    def test_non_model_object_with_meta(self):
        res = self.client.get('/detail/nonmodel/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'].id, "non_model_1")
