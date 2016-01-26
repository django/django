# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin

from .models import Artist, Author, Book, Page


@override_settings(ROOT_URLCONF='generic_views.urls')
class DetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.artist1 = Artist.objects.create(name='Rene Magritte')
        cls.author1 = Author.objects.create(name='Roberto Bolaño', slug='roberto-bolano')
        cls.author2 = Author.objects.create(name='Scott Rosenberg', slug='scott-rosenberg')
        cls.book1 = Book.objects.create(name='2066', slug='2066', pages=800, pubdate=datetime.date(2008, 10, 1))
        cls.book1.authors.add(cls.author1)
        cls.book2 = Book.objects.create(
            name='Dreaming in Code', slug='dreaming-in-code', pages=300, pubdate=datetime.date(2006, 5, 1)
        )
        cls.page1 = Page.objects.create(
            content='I was once bitten by a moose.', template='generic_views/page_template.html'
        )

    def test_simple_object(self):
        res = self.client.get('/detail/obj/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], {'foo': 'bar'})
        self.assertIsInstance(res.context['view'], View)
        self.assertTemplateUsed(res, 'generic_views/detail.html')

    def test_detail_by_pk(self):
        res = self.client.get('/detail/author/%s/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_missing_object(self):
        res = self.client.get('/detail/author/500/')
        self.assertEqual(res.status_code, 404)

    def test_detail_object_does_not_exist(self):
        self.assertRaises(ObjectDoesNotExist, self.client.get, '/detail/doesnotexist/1/')

    def test_detail_by_custom_pk(self):
        res = self.client.get('/detail/author/bycustompk/%s/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
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
        res = self.client.get('/detail/author/bypkignoreslug/%s-roberto-bolano/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_ignore_slug_mismatch(self):
        res = self.client.get('/detail/author/bypkignoreslug/%s-scott-rosenberg/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_and_slug(self):
        res = self.client.get('/detail/author/bypkandslug/%s-roberto-bolano/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_detail_by_pk_and_slug_mismatch_404(self):
        res = self.client.get('/detail/author/bypkandslug/%s-scott-rosenberg/' % self.author1.pk)
        self.assertEqual(res.status_code, 404)

    def test_verbose_name(self):
        res = self.client.get('/detail/artist/%s/' % self.artist1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.artist1)
        self.assertEqual(res.context['artist'], self.artist1)
        self.assertTemplateUsed(res, 'generic_views/artist_detail.html')

    def test_template_name(self):
        res = self.client.get('/detail/author/%s/template_name/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/about.html')

    def test_template_name_suffix(self):
        res = self.client.get('/detail/author/%s/template_name_suffix/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['author'], self.author1)
        self.assertTemplateUsed(res, 'generic_views/author_view.html')

    def test_template_name_field(self):
        res = self.client.get('/detail/page/%s/field/' % self.page1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.page1)
        self.assertEqual(res.context['page'], self.page1)
        self.assertTemplateUsed(res, 'generic_views/page_template.html')

    def test_context_object_name(self):
        res = self.client.get('/detail/author/%s/context_object_name/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertEqual(res.context['thingy'], self.author1)
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_duplicated_context_object_name(self):
        res = self.client.get('/detail/author/%s/dupe_context_object_name/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], self.author1)
        self.assertNotIn('author', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_custom_detail(self):
        """
        AuthorCustomDetail overrides get() and ensures that
        SingleObjectMixin.get_context_object_name() always uses the obj
        parameter instead of self.object.
        """
        res = self.client.get('/detail/author/%s/custom_detail/' % self.author1.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['custom_author'], self.author1)
        self.assertNotIn('author', res.context)
        self.assertNotIn('object', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_detail.html')

    def test_deferred_queryset_template_name(self):
        class FormContext(SingleObjectTemplateResponseMixin):
            request = RequestFactory().get('/')
            model = Author
            object = Author.objects.defer('name').get(pk=self.author1.pk)

        self.assertEqual(FormContext().get_template_names()[0], 'generic_views/author_detail.html')

    def test_deferred_queryset_context_object_name(self):
        class FormContext(ModelFormMixin):
            request = RequestFactory().get('/')
            model = Author
            object = Author.objects.defer('name').get(pk=self.author1.pk)
            fields = ('name',)

        form_context_data = FormContext().get_context_data()
        self.assertEqual(form_context_data['object'], self.author1)
        self.assertEqual(form_context_data['author'], self.author1)

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')

    def test_non_model_object_with_meta(self):
        res = self.client.get('/detail/nonmodel/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'].id, "non_model_1")
