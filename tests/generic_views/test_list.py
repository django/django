from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import TestCase, override_settings, RequestFactory
from django.views.generic.base import View
from django.utils.encoding import force_str

from .models import Author, Artist
from . import views


class ListViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'generic_views.urls'
    rf = RequestFactory()

    def _get_view_context(self, view_class, initkwargs=None, kwargs=None):
        initkwargs = initkwargs or {}
        kwargs = kwargs or {}
        test_view = view_class(**initkwargs).setup(self.rf.get('/'), **kwargs)
        test_view.object_list = test_view.get_queryset()

        return test_view.get_context_data()

    def test_items(self):
        context = self._get_view_context(views.DictList)
        self.assertEqual(context['object_list'][0]['first'], 'John')

    def test_queryset(self):
        context = self._get_view_context(views.AuthorList)

        self.assertEqual(list(context['object_list']), list(Author.objects.all()))
        self.assertIsInstance(context['view'], View)
        self.assertIs(context['author_list'], context['object_list'])
        self.assertIsNone(context['paginator'])
        self.assertIsNone(context['page_obj'])
        self.assertFalse(context['is_paginated'])

    def test_paginated_queryset(self):
        self._make_authors(100)
        context = self._get_view_context(views.AuthorList, {'paginate_by': 30})

        self.assertEqual(len(context['object_list']), 30)
        self.assertIs(context['author_list'], context['object_list'])
        self.assertTrue(context['is_paginated'])
        self.assertEqual(context['page_obj'].number, 1)
        self.assertEqual(context['paginator'].num_pages, 4)
        self.assertEqual(context['author_list'][0].name, 'Author 00')
        self.assertEqual(list(context['author_list'])[-1].name, 'Author 29')

    def test_paginated_queryset_shortdata(self):
        # Test that short datasets ALSO result in a paginated view.
        context = self._get_view_context(views.AuthorList, {'paginate_by': 30})

        self.assertEqual(list(context['object_list']), list(Author.objects.all()))
        self.assertIs(context['author_list'], context['object_list'])
        self.assertEqual(context['page_obj'].number, 1)
        self.assertEqual(context['paginator'].num_pages, 1)
        self.assertFalse(context['is_paginated'])

    def test_paginated_get_page(self):
        self._make_authors(100)
        context = self._get_view_context(views.AuthorList, {'paginate_by': 30}, {'page': 2})

        self.assertEqual(len(context['object_list']), 30)
        self.assertIs(context['author_list'], context['object_list'])
        self.assertEqual(context['author_list'][0].name, 'Author 30')
        self.assertEqual(context['page_obj'].number, 2)

    def test_paginated_get_last_page(self):
        self._make_authors(100)
        context = self._get_view_context(views.AuthorList, {'paginate_by': 30}, {'page': 'last'})

        self.assertEqual(len(context['object_list']), 10)
        self.assertIs(context['author_list'], context['object_list'])
        self.assertEqual(context['author_list'][0].name, 'Author 90')
        self.assertEqual(context['page_obj'].number, 4)

    def test_paginated_get_page_by_urlvar(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/3/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 60')
        self.assertEqual(res.context['page_obj'].number, 3)

    def test_paginated_get_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': '3'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 60')
        self.assertEqual(res.context['page_obj'].number, 3)

    def test_paginated_page_out_of_range(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/42/')
        self.assertEqual(res.status_code, 404)

    def test_paginated_invalid_page(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/?page=frog')
        self.assertEqual(res.status_code, 404)

    def test_paginated_custom_paginator_class(self):
        self._make_authors(7)
        initkwargs = {
            'paginate_by': 5,
            'paginator_class': views.CustomPaginator
        }
        context = self._get_view_context(views.AuthorList, initkwargs)

        self.assertEqual(context['paginator'].num_pages, 1)
        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(context['object_list']), 7)

    def test_paginated_custom_page_kwarg(self):
        self._make_authors(100)
        initkwargs = {
            'paginate_by': 30,
            'page_kwarg': 'pagina'
        }
        context = self._get_view_context(views.AuthorList, initkwargs, {'pagina': 2})

        self.assertEqual(len(context['object_list']), 30)
        self.assertIs(context['author_list'], context['object_list'])
        self.assertEqual(context['author_list'][0].name, 'Author 30')
        self.assertEqual(context['page_obj'].number, 2)

    def test_paginated_custom_paginator_constructor(self):
        self._make_authors(7)
        context = self._get_view_context(views.AuthorListCustomPaginator)

        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(context['object_list']), 7)

    def test_paginated_orphaned_queryset(self):
        self._make_authors(92)
        initkwargs = {
            'paginate_by': 30,
            'paginate_orphans': 2
        }
        context = self._get_view_context(views.AuthorList, initkwargs)
        self.assertEqual(context['page_obj'].number, 1)

        context = self._get_view_context(views.AuthorList, initkwargs, {'page': 'last'})
        self.assertEqual(context['page_obj'].number, 3)

        context = self._get_view_context(views.AuthorList, initkwargs, {'page': '3'})
        self.assertEqual(context['page_obj'].number, 3)

        with self.assertRaises(Http404):
            self._get_view_context(views.AuthorList, initkwargs, {'page': '4'})

    def test_paginated_non_queryset(self):
        context = self._get_view_context(views.DictList, {'paginate_by': 1})
        self.assertEqual(len(context['object_list']), 1)

    def test_verbose_name(self):
        context = self._get_view_context(views.ArtistList)

        self.assertEqual(list(context['object_list']), list(Artist.objects.all()))
        self.assertIs(context['artist_list'], context['object_list'])
        self.assertIsNone(context['paginator'])
        self.assertIsNone(context['page_obj'])
        self.assertFalse(context['is_paginated'])

    def test_allow_empty_false(self):
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 200)
        Author.objects.all().delete()
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 404)

    def test_template_name(self):
        res = self.client.get('/list/authors/template_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'generic_views/list.html')

    def test_template_name_suffix(self):
        res = self.client.get('/list/authors/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'generic_views/author_objects.html')

    def test_context_object_name(self):
        context = self._get_view_context(views.AuthorList, {'context_object_name': 'author_list'})
        self.assertEqual(list(context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', context)
        self.assertIs(context['author_list'], context['object_list'])

    def test_duplicate_context_object_name(self):
        context = self._get_view_context(views.AuthorList, {'context_object_name': 'object_list'})
        self.assertEqual(list(context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', context)
        self.assertNotIn('author_list', context)

    def test_missing_items(self):
        with self.assertRaises(ImproperlyConfigured):
            self._get_view_context(views.AuthorList, {'queryset': None})

    def test_paginated_list_view_does_not_load_entire_table(self):
        # Regression test for #17535
        self._make_authors(3)
        # 1 query for authors
        with self.assertNumQueries(1):
            self.client.get('/list/authors/notempty/')
        # same as above + 1 query to test if authors exist + 1 query for pagination
        with self.assertNumQueries(3):
            self.client.get('/list/authors/notempty/paginated/')

    @override_settings(DEBUG=True)
    def test_paginated_list_view_returns_useful_message_on_invalid_page(self):
        # test for #19240
        # tests that source exception's message is included in page
        self._make_authors(1)
        res = self.client.get('/list/authors/paginated/2/')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(force_str(res.context.get('reason')),
                "Invalid page (2): That page contains no results")

    def _make_authors(self, n):
        Author.objects.all().delete()
        for i in range(n):
            Author.objects.create(name='Author %02i' % i, slug='a%s' % i)
