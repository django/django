from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
from django.views.generic.base import View
from django.utils.encoding import force_str

from .models import Author, Artist


class ListViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'regressiontests.generic_views.urls'

    def test_items(self):
        res = self.client.get('/list/dict/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/list.html')
        self.assertEqual(res.context['object_list'][0]['first'], 'John')

    def test_queryset(self):
        res = self.client.get('/list/authors/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertTrue(isinstance(res.context['view'], View))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertIsNone(res.context['paginator'])
        self.assertIsNone(res.context['page_obj'])
        self.assertFalse(res.context['is_paginated'])

    def test_paginated_queryset(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTrue(res.context['is_paginated'])
        self.assertEqual(res.context['page_obj'].number, 1)
        self.assertEqual(res.context['paginator'].num_pages, 4)
        self.assertEqual(res.context['author_list'][0].name, 'Author 00')
        self.assertEqual(list(res.context['author_list'])[-1].name, 'Author 29')

    def test_paginated_queryset_shortdata(self):
        # Test that short datasets ALSO result in a paginated view.
        res = self.client.get('/list/authors/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['page_obj'].number, 1)
        self.assertEqual(res.context['paginator'].num_pages, 1)
        self.assertFalse(res.context['is_paginated'])

    def test_paginated_get_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': '2'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 30')
        self.assertEqual(res.context['page_obj'].number, 2)

    def test_paginated_get_last_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': 'last'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['object_list']), 10)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 90')
        self.assertEqual(res.context['page_obj'].number, 4)

    def test_paginated_get_page_by_urlvar(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/3/')
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
        res = self.client.get('/list/authors/paginated/custom_class/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['paginator'].num_pages, 1)
        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(res.context['object_list']), 7)

    def test_paginated_custom_page_kwarg(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/custom_page_kwarg/', {'pagina': '2'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 30')
        self.assertEqual(res.context['page_obj'].number, 2)

    def test_paginated_custom_paginator_constructor(self):
        self._make_authors(7)
        res = self.client.get('/list/authors/paginated/custom_constructor/')
        self.assertEqual(res.status_code, 200)
        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(res.context['object_list']), 7)

    def test_paginated_orphaned_queryset(self):
        self._make_authors(92)
        res = self.client.get('/list/authors/paginated-orphaned/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 1)
        res = self.client.get(
            '/list/authors/paginated-orphaned/', {'page': 'last'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 3)
        res = self.client.get(
            '/list/authors/paginated-orphaned/', {'page': '3'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['page_obj'].number, 3)
        res = self.client.get(
            '/list/authors/paginated-orphaned/', {'page': '4'})
        self.assertEqual(res.status_code, 404)

    def test_paginated_non_queryset(self):
        res = self.client.get('/list/dict/paginated/')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['object_list']), 1)

    def test_verbose_name(self):
        res = self.client.get('/list/artists/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'generic_views/list.html')
        self.assertEqual(list(res.context['object_list']), list(Artist.objects.all()))
        self.assertIs(res.context['artist_list'], res.context['object_list'])
        self.assertIsNone(res.context['paginator'])
        self.assertIsNone(res.context['page_obj'])
        self.assertFalse(res.context['is_paginated'])

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
        res = self.client.get('/list/authors/context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', res.context)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'generic_views/author_list.html')

    def test_duplicate_context_object_name(self):
        res = self.client.get('/list/authors/dupe_context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', res.context)
        self.assertNotIn('author_list', res.context)
        self.assertTemplateUsed(res, 'generic_views/author_list.html')

    def test_missing_items(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/list/authors/invalid/')

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
