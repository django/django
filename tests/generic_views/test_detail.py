from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import Http404
from django.test import TestCase, RequestFactory
from django.views.generic.base import View

from .models import Artist, Author, Page
from . import views


class DetailViewTest(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'generic_views.urls'
    rf = RequestFactory()

    def _get_view_context(self, view_class, initkwargs=None, kwargs=None):
        initkwargs = initkwargs or {}
        kwargs = kwargs or {}
        test_view = view_class(**initkwargs).setup(self.rf.get('/'), **kwargs)
        test_view.object = test_view.get_object()

        return test_view.get_context_data()

    def test_simple_object(self):
        context = self._get_view_context(views.ObjectDetail)
        self.assertEqual(context['object'], {'foo': 'bar'})
        self.assertIsInstance(context['view'], View)

    def test_detail_by_pk(self):
        context = self._get_view_context(views.AuthorDetail, None, {'pk': 1})
        author = Author.objects.get(pk=1)
        self.assertEqual(context['object'], author)
        self.assertEqual(context['author'], author)

    def test_detail_missing_object(self):
        with self.assertRaises(Http404):
            self._get_view_context(views.AuthorDetail, None, {'pk': 500})

    def test_detail_object_does_not_exist(self):
        with self.assertRaises(ObjectDoesNotExist):
            self._get_view_context(views.ObjectDoesNotExistDetail, None, {'pk': 1})

    def test_detail_by_custom_pk(self):
        context = self._get_view_context(views.AuthorDetail, {'pk_url_kwarg': 'foo'}, {'foo': 1})
        author = Author.objects.get(pk=1)
        self.assertEqual(context['object'], author)
        self.assertEqual(context['author'], author)

    def test_detail_by_slug(self):
        context = self._get_view_context(views.AuthorDetail, None, {'slug': 'scott-rosenberg'})
        author = Author.objects.get(slug='scott-rosenberg')
        self.assertEqual(context['object'], author)
        self.assertEqual(context['author'], author)

    def test_detail_by_custom_slug(self):
        context = self._get_view_context(
            views.AuthorDetail, {'slug_url_kwarg': 'foo'}, {'foo': 'scott-rosenberg'}
        )
        author = Author.objects.get(slug='scott-rosenberg')
        self.assertEqual(context['object'], author)
        self.assertEqual(context['author'], author)

    def test_template_name(self):
        res = self.client.get('/detail/author/1/template_name/')
        self.assertEqual(res.status_code, 200)
        author = Author.objects.get(pk=1)
        self.assertEqual(res.context['object'], author)
        self.assertEqual(res.context['author'], author)
        self.assertTemplateUsed(res, 'generic_views/about.html')

    def test_template_name_suffix(self):
        res = self.client.get('/detail/author/1/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        author = Author.objects.get(pk=1)
        self.assertEqual(res.context['object'], author)
        self.assertEqual(res.context['author'], author)
        self.assertTemplateUsed(res, 'generic_views/author_view.html')

    def test_template_name_field(self):
        res = self.client.get('/detail/page/1/field/')
        self.assertEqual(res.status_code, 200)
        page = Page.objects.get(pk=1)
        self.assertEqual(res.context['object'], page)
        self.assertEqual(res.context['page'], page)
        self.assertTemplateUsed(res, 'generic_views/page_template.html')

    def test_context_object_name(self):
        context = self._get_view_context(
            views.AuthorDetail, {'context_object_name': 'thingy'}, {'pk': 1}
        )
        author = Author.objects.get(pk=1)
        self.assertEqual(context['object'], author)
        self.assertEqual(context['thingy'], author)
        self.assertFalse('author' in context)

    def test_duplicated_context_object_name(self):
        context = self._get_view_context(
            views.AuthorDetail, {'context_object_name': 'object'}, {'pk': 1}
        )
        self.assertEqual(context['object'], Author.objects.get(pk=1))
        self.assertFalse('author' in context)

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')

    def test_non_model_object_with_meta(self):
        context = self._get_view_context(views.NonModelDetail, None, {'pk': 1})
        self.assertEqual(context['object'].id, "non_model_1")
