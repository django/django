from __future__ import unicode_literals

import unittest
import warnings
from datetime import datetime

from django.core.paginator import (
    EmptyPage, InvalidPage, PageNotAnInteger, Paginator,
    UnorderedObjectListWarning,
)
from django.test import TestCase
from django.utils import six

from .custom import ValidAdjacentNumsPaginator
from .models import Article


class PaginationTests(unittest.TestCase):
    """
    Tests for the Paginator and Page classes.
    """

    def check_paginator(self, params, output):
        """
        Helper method that instantiates a Paginator object from the passed
        params and then checks that its attributes match the passed output.
        """
        count, num_pages, page_range = output
        paginator = Paginator(*params)
        self.check_attribute('count', paginator, count, params)
        self.check_attribute('num_pages', paginator, num_pages, params)
        self.check_attribute('page_range', paginator, page_range, params, coerce=list)

    def check_attribute(self, name, paginator, expected, params, coerce=None):
        """
        Helper method that checks a single attribute and gives a nice error
        message upon test failure.
        """
        got = getattr(paginator, name)
        if coerce is not None:
            got = coerce(got)
        self.assertEqual(
            expected, got,
            "For '%s', expected %s but got %s.  Paginator parameters were: %s"
            % (name, expected, got, params)
        )

    def test_paginator(self):
        """
        Tests the paginator attributes using varying inputs.
        """
        nine = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        ten = nine + [10]
        eleven = ten + [11]
        tests = (
            # Each item is two tuples:
            #     First tuple is Paginator parameters - object_list, per_page,
            #         orphans, and allow_empty_first_page.
            #     Second tuple is resulting Paginator attributes - count,
            #         num_pages, and page_range.
            # Ten items, varying orphans, no empty first page.
            ((ten, 4, 0, False), (10, 3, [1, 2, 3])),
            ((ten, 4, 1, False), (10, 3, [1, 2, 3])),
            ((ten, 4, 2, False), (10, 2, [1, 2])),
            ((ten, 4, 5, False), (10, 2, [1, 2])),
            ((ten, 4, 6, False), (10, 1, [1])),
            # Ten items, varying orphans, allow empty first page.
            ((ten, 4, 0, True), (10, 3, [1, 2, 3])),
            ((ten, 4, 1, True), (10, 3, [1, 2, 3])),
            ((ten, 4, 2, True), (10, 2, [1, 2])),
            ((ten, 4, 5, True), (10, 2, [1, 2])),
            ((ten, 4, 6, True), (10, 1, [1])),
            # One item, varying orphans, no empty first page.
            (([1], 4, 0, False), (1, 1, [1])),
            (([1], 4, 1, False), (1, 1, [1])),
            (([1], 4, 2, False), (1, 1, [1])),
            # One item, varying orphans, allow empty first page.
            (([1], 4, 0, True), (1, 1, [1])),
            (([1], 4, 1, True), (1, 1, [1])),
            (([1], 4, 2, True), (1, 1, [1])),
            # Zero items, varying orphans, no empty first page.
            (([], 4, 0, False), (0, 0, [])),
            (([], 4, 1, False), (0, 0, [])),
            (([], 4, 2, False), (0, 0, [])),
            # Zero items, varying orphans, allow empty first page.
            (([], 4, 0, True), (0, 1, [1])),
            (([], 4, 1, True), (0, 1, [1])),
            (([], 4, 2, True), (0, 1, [1])),
            # Number if items one less than per_page.
            (([], 1, 0, True), (0, 1, [1])),
            (([], 1, 0, False), (0, 0, [])),
            (([1], 2, 0, True), (1, 1, [1])),
            ((nine, 10, 0, True), (9, 1, [1])),
            # Number if items equal to per_page.
            (([1], 1, 0, True), (1, 1, [1])),
            (([1, 2], 2, 0, True), (2, 1, [1])),
            ((ten, 10, 0, True), (10, 1, [1])),
            # Number if items one more than per_page.
            (([1, 2], 1, 0, True), (2, 2, [1, 2])),
            (([1, 2, 3], 2, 0, True), (3, 2, [1, 2])),
            ((eleven, 10, 0, True), (11, 2, [1, 2])),
            # Number if items one more than per_page with one orphan.
            (([1, 2], 1, 1, True), (2, 1, [1])),
            (([1, 2, 3], 2, 1, True), (3, 1, [1])),
            ((eleven, 10, 1, True), (11, 1, [1])),
            # Non-integer inputs
            ((ten, '4', 1, False), (10, 3, [1, 2, 3])),
            ((ten, '4', 1, False), (10, 3, [1, 2, 3])),
            ((ten, 4, '1', False), (10, 3, [1, 2, 3])),
            ((ten, 4, '1', False), (10, 3, [1, 2, 3])),
        )
        for params, output in tests:
            self.check_paginator(params, output)

    def test_invalid_page_number(self):
        """
        Invalid page numbers result in the correct exception being raised.
        """
        paginator = Paginator([1, 2, 3], 2)
        with self.assertRaises(InvalidPage):
            paginator.page(3)
        with self.assertRaises(PageNotAnInteger):
            paginator.validate_number(None)
        with self.assertRaises(PageNotAnInteger):
            paginator.validate_number('x')
        # With no content and allow_empty_first_page=True, 1 is a valid page number
        paginator = Paginator([], 2)
        self.assertEqual(paginator.validate_number(1), 1)

    def test_paginate_misc_classes(self):
        class CountContainer(object):
            def count(self):
                return 42
        # Paginator can be passed other objects with a count() method.
        paginator = Paginator(CountContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], list(paginator.page_range))

        # Paginator can be passed other objects that implement __len__.
        class LenContainer(object):
            def __len__(self):
                return 42
        paginator = Paginator(LenContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], list(paginator.page_range))

    def check_indexes(self, params, page_num, indexes):
        """
        Helper method that instantiates a Paginator object from the passed
        params and then checks that the start and end indexes of the passed
        page_num match those given as a 2-tuple in indexes.
        """
        paginator = Paginator(*params)
        if page_num == 'first':
            page_num = 1
        elif page_num == 'last':
            page_num = paginator.num_pages
        page = paginator.page(page_num)
        start, end = indexes
        msg = ("For %s of page %s, expected %s but got %s. Paginator parameters were: %s")
        self.assertEqual(start, page.start_index(), msg % ('start index', page_num, start, page.start_index(), params))
        self.assertEqual(end, page.end_index(), msg % ('end index', page_num, end, page.end_index(), params))

    def test_page_indexes(self):
        """
        Paginator pages have the correct start and end indexes.
        """
        ten = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tests = (
            # Each item is three tuples:
            #     First tuple is Paginator parameters - object_list, per_page,
            #         orphans, and allow_empty_first_page.
            #     Second tuple is the start and end indexes of the first page.
            #     Third tuple is the start and end indexes of the last page.
            # Ten items, varying per_page, no orphans.
            ((ten, 1, 0, True), (1, 1), (10, 10)),
            ((ten, 2, 0, True), (1, 2), (9, 10)),
            ((ten, 3, 0, True), (1, 3), (10, 10)),
            ((ten, 5, 0, True), (1, 5), (6, 10)),
            # Ten items, varying per_page, with orphans.
            ((ten, 1, 1, True), (1, 1), (9, 10)),
            ((ten, 1, 2, True), (1, 1), (8, 10)),
            ((ten, 3, 1, True), (1, 3), (7, 10)),
            ((ten, 3, 2, True), (1, 3), (7, 10)),
            ((ten, 3, 4, True), (1, 3), (4, 10)),
            ((ten, 5, 1, True), (1, 5), (6, 10)),
            ((ten, 5, 2, True), (1, 5), (6, 10)),
            ((ten, 5, 5, True), (1, 10), (1, 10)),
            # One item, varying orphans, no empty first page.
            (([1], 4, 0, False), (1, 1), (1, 1)),
            (([1], 4, 1, False), (1, 1), (1, 1)),
            (([1], 4, 2, False), (1, 1), (1, 1)),
            # One item, varying orphans, allow empty first page.
            (([1], 4, 0, True), (1, 1), (1, 1)),
            (([1], 4, 1, True), (1, 1), (1, 1)),
            (([1], 4, 2, True), (1, 1), (1, 1)),
            # Zero items, varying orphans, allow empty first page.
            (([], 4, 0, True), (0, 0), (0, 0)),
            (([], 4, 1, True), (0, 0), (0, 0)),
            (([], 4, 2, True), (0, 0), (0, 0)),
        )
        for params, first, last in tests:
            self.check_indexes(params, 'first', first)
            self.check_indexes(params, 'last', last)

        # When no items and no empty first page, we should get EmptyPage error.
        with self.assertRaises(EmptyPage):
            self.check_indexes(([], 4, 0, False), 1, None)
        with self.assertRaises(EmptyPage):
            self.check_indexes(([], 4, 1, False), 1, None)
        with self.assertRaises(EmptyPage):
            self.check_indexes(([], 4, 2, False), 1, None)

    def test_page_sequence(self):
        """
        A paginator page acts like a standard sequence.
        """
        eleven = 'abcdefghijk'
        page2 = Paginator(eleven, per_page=5, orphans=1).page(2)
        self.assertEqual(len(page2), 6)
        self.assertIn('k', page2)
        self.assertNotIn('a', page2)
        self.assertEqual(''.join(page2), 'fghijk')
        self.assertEqual(''.join(reversed(page2)), 'kjihgf')

    def test_get_page_hook(self):
        """
        A Paginator subclass can use the ``_get_page`` hook to
        return an alternative to the standard Page class.
        """
        eleven = 'abcdefghijk'
        paginator = ValidAdjacentNumsPaginator(eleven, per_page=6)
        page1 = paginator.page(1)
        page2 = paginator.page(2)
        self.assertIsNone(page1.previous_page_number())
        self.assertEqual(page1.next_page_number(), 2)
        self.assertEqual(page2.previous_page_number(), 1)
        self.assertIsNone(page2.next_page_number())

    def test_page_range_iterator(self):
        """
        Paginator.page_range should be an iterator.
        """
        self.assertIsInstance(Paginator([1, 2, 3], 2).page_range, type(six.moves.range(0)))


class ModelPaginationTests(TestCase):
    """
    Test pagination with Django model instances
    """
    def setUp(self):
        # Prepare a list of objects for pagination.
        for x in range(1, 10):
            a = Article(headline='Article %s' % x, pub_date=datetime(2005, 7, 29))
            a.save()

    def test_first_page(self):
        paginator = Paginator(Article.objects.order_by('id'), 5)
        p = paginator.page(1)
        self.assertEqual("<Page 1 of 2>", six.text_type(p))
        self.assertQuerysetEqual(p.object_list, [
            "<Article: Article 1>",
            "<Article: Article 2>",
            "<Article: Article 3>",
            "<Article: Article 4>",
            "<Article: Article 5>"
        ])
        self.assertTrue(p.has_next())
        self.assertFalse(p.has_previous())
        self.assertTrue(p.has_other_pages())
        self.assertEqual(2, p.next_page_number())
        with self.assertRaises(InvalidPage):
            p.previous_page_number()
        self.assertEqual(1, p.start_index())
        self.assertEqual(5, p.end_index())

    def test_last_page(self):
        paginator = Paginator(Article.objects.order_by('id'), 5)
        p = paginator.page(2)
        self.assertEqual("<Page 2 of 2>", six.text_type(p))
        self.assertQuerysetEqual(p.object_list, [
            "<Article: Article 6>",
            "<Article: Article 7>",
            "<Article: Article 8>",
            "<Article: Article 9>"
        ])
        self.assertFalse(p.has_next())
        self.assertTrue(p.has_previous())
        self.assertTrue(p.has_other_pages())
        with self.assertRaises(InvalidPage):
            p.next_page_number()
        self.assertEqual(1, p.previous_page_number())
        self.assertEqual(6, p.start_index())
        self.assertEqual(9, p.end_index())

    def test_page_getitem(self):
        """
        Tests proper behavior of a paginator page __getitem__ (queryset
        evaluation, slicing, exception raised).
        """
        paginator = Paginator(Article.objects.order_by('id'), 5)
        p = paginator.page(1)

        # Make sure object_list queryset is not evaluated by an invalid __getitem__ call.
        # (this happens from the template engine when using eg: {% page_obj.has_previous %})
        self.assertIsNone(p.object_list._result_cache)
        with self.assertRaises(TypeError):
            p['has_previous']
        self.assertIsNone(p.object_list._result_cache)
        self.assertNotIsInstance(p.object_list, list)

        # Make sure slicing the Page object with numbers and slice objects work.
        self.assertEqual(p[0], Article.objects.get(headline='Article 1'))
        self.assertQuerysetEqual(p[slice(2)], [
            "<Article: Article 1>",
            "<Article: Article 2>",
        ]
        )
        # After __getitem__ is called, object_list is a list
        self.assertIsInstance(p.object_list, list)

    def test_paginating_unordered_queryset_raises_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            # Prevent the RuntimeWarning subclass from appearing as an
            # exception due to the warnings.simplefilter() in runtests.py.
            warnings.filterwarnings('always', category=UnorderedObjectListWarning)
            Paginator(Article.objects.all(), 5)
        self.assertEqual(len(warns), 1)
        warning = warns[0]
        self.assertEqual(str(warning.message), (
            "Pagination may yield inconsistent results with an unordered "
            "object_list: <QuerySet [<Article: Article 1>, "
            "<Article: Article 2>, <Article: Article 3>, <Article: Article 4>, "
            "<Article: Article 5>, <Article: Article 6>, <Article: Article 7>, "
            "<Article: Article 8>, <Article: Article 9>]>"
        ))
        # The warning points at the Paginator caller (i.e. the stacklevel
        # is appropriate).
        self.assertEqual(warning.filename, __file__)
