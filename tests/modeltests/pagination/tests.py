from __future__ import absolute_import

from datetime import datetime

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.test import TestCase

from .models import Article


class CountContainer(object):
    def count(self):
        return 42

class LenContainer(object):
    def __len__(self):
        return 42

class PaginationTests(TestCase):
    def setUp(self):
        # Prepare a list of objects for pagination.
        for x in range(1, 10):
            a = Article(headline='Article %s' % x, pub_date=datetime(2005, 7, 29))
            a.save()

    def test_paginator(self):
        paginator = Paginator(Article.objects.all(), 5)
        self.assertEqual(9, paginator.count)
        self.assertEqual(2, paginator.num_pages)
        self.assertEqual([1, 2], paginator.page_range)

    def test_first_page(self):
        paginator = Paginator(Article.objects.all(), 5)
        p = paginator.page(1)
        self.assertEqual(u"<Page 1 of 2>", unicode(p))
        self.assertQuerysetEqual(p.object_list, [
                "<Article: Article 1>",
                "<Article: Article 2>",
                "<Article: Article 3>",
                "<Article: Article 4>",
                "<Article: Article 5>"
            ]
        )
        self.assertTrue(p.has_next())
        self.assertFalse(p.has_previous())
        self.assertTrue(p.has_other_pages())
        self.assertEqual(2, p.next_page_number())
        self.assertEqual(0, p.previous_page_number())
        self.assertEqual(1, p.start_index())
        self.assertEqual(5, p.end_index())

    def test_last_page(self):
        paginator = Paginator(Article.objects.all(), 5)
        p = paginator.page(2)
        self.assertEqual(u"<Page 2 of 2>", unicode(p))
        self.assertQuerysetEqual(p.object_list, [
                "<Article: Article 6>",
                "<Article: Article 7>",
                "<Article: Article 8>",
                "<Article: Article 9>"
            ]
        )
        self.assertFalse(p.has_next())
        self.assertTrue(p.has_previous())
        self.assertTrue(p.has_other_pages())
        self.assertEqual(3, p.next_page_number())
        self.assertEqual(1, p.previous_page_number())
        self.assertEqual(6, p.start_index())
        self.assertEqual(9, p.end_index())

    def test_empty_page(self):
        paginator = Paginator(Article.objects.all(), 5)
        self.assertRaises(EmptyPage, paginator.page, 0)
        self.assertRaises(EmptyPage, paginator.page, 3)

        # Empty paginators with allow_empty_first_page=True.
        paginator = Paginator(Article.objects.filter(id=0), 5, allow_empty_first_page=True)
        self.assertEqual(0, paginator.count)
        self.assertEqual(1, paginator.num_pages)
        self.assertEqual([1], paginator.page_range)

        # Empty paginators with allow_empty_first_page=False.
        paginator = Paginator(Article.objects.filter(id=0), 5, allow_empty_first_page=False)
        self.assertEqual(0, paginator.count)
        self.assertEqual(0, paginator.num_pages)
        self.assertEqual([], paginator.page_range)

    def test_invalid_page(self):
        paginator = Paginator(Article.objects.all(), 5)
        self.assertRaises(InvalidPage, paginator.page, 7)

    def test_orphans(self):
        # Add a few more records to test out the orphans feature.
        for x in range(10, 13):
            Article(headline="Article %s" % x, pub_date=datetime(2006, 10, 6)).save()

        # With orphans set to 3 and 10 items per page, we should get all 12 items on a single page.
        paginator = Paginator(Article.objects.all(), 10, orphans=3)
        self.assertEqual(1, paginator.num_pages)

        # With orphans only set to 1, we should get two pages.
        paginator = Paginator(Article.objects.all(), 10, orphans=1)
        self.assertEqual(2, paginator.num_pages)

    def test_paginate_list(self):
        # Paginators work with regular lists/tuples, too -- not just with QuerySets.
        paginator = Paginator([1, 2, 3, 4, 5, 6, 7, 8, 9], 5)
        self.assertEqual(9, paginator.count)
        self.assertEqual(2, paginator.num_pages)
        self.assertEqual([1, 2], paginator.page_range)
        p = paginator.page(1)
        self.assertEqual(u"<Page 1 of 2>", unicode(p))
        self.assertEqual([1, 2, 3, 4, 5], p.object_list)
        self.assertTrue(p.has_next())
        self.assertFalse(p.has_previous())
        self.assertTrue(p.has_other_pages())
        self.assertEqual(2, p.next_page_number())
        self.assertEqual(0, p.previous_page_number())
        self.assertEqual(1, p.start_index())
        self.assertEqual(5, p.end_index())

    def test_paginate_misc_classes(self):
        # Paginator can be passed other objects with a count() method.
        paginator = Paginator(CountContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], paginator.page_range)

        # Paginator can be passed other objects that implement __len__.
        paginator = Paginator(LenContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], paginator.page_range)
