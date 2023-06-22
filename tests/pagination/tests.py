import collections.abc
import unittest.mock
import warnings
from datetime import datetime

from django.core.paginator import (
    EmptyPage,
    InvalidPage,
    PageNotAnInteger,
    Paginator,
    UnorderedObjectListWarning,
)
from django.test import SimpleTestCase, TestCase

from .custom import ValidAdjacentNumsPaginator
from .models import Article


class PaginationTests(SimpleTestCase):
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
        self.check_attribute("count", paginator, count, params)
        self.check_attribute("num_pages", paginator, num_pages, params)
        self.check_attribute("page_range", paginator, page_range, params, coerce=list)

    def check_attribute(self, name, paginator, expected, params, coerce=None):
        """
        Helper method that checks a single attribute and gives a nice error
        message upon test failure.
        """
        got = getattr(paginator, name)
        if coerce is not None:
            got = coerce(got)
        self.assertEqual(
            expected,
            got,
            "For '%s', expected %s but got %s.  Paginator parameters were: %s"
            % (name, expected, got, params),
        )

    def test_paginator(self):
        """
        Tests the paginator attributes using varying inputs.
        """
        nine = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        ten = nine + [10]
        eleven = ten + [11]
        tests = (
            # Each item is 2-tuple:
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
            ((ten, "4", 1, False), (10, 3, [1, 2, 3])),
            ((ten, "4", 1, False), (10, 3, [1, 2, 3])),
            ((ten, 4, "1", False), (10, 3, [1, 2, 3])),
            ((ten, 4, "1", False), (10, 3, [1, 2, 3])),
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
            paginator.validate_number("x")
        with self.assertRaises(PageNotAnInteger):
            paginator.validate_number(1.2)

    def test_error_messages(self):
        error_messages = {
            "invalid_page": "Wrong page number",
            "min_page": "Too small",
            "no_results": "There is nothing here",
        }
        paginator = Paginator([1, 2, 3], 2, error_messages=error_messages)
        msg = "Wrong page number"
        with self.assertRaisesMessage(PageNotAnInteger, msg):
            paginator.validate_number(1.2)
        msg = "Too small"
        with self.assertRaisesMessage(EmptyPage, msg):
            paginator.validate_number(-1)
        msg = "There is nothing here"
        with self.assertRaisesMessage(EmptyPage, msg):
            paginator.validate_number(3)

        error_messages = {"min_page": "Too small"}
        paginator = Paginator([1, 2, 3], 2, error_messages=error_messages)
        # Custom message.
        msg = "Too small"
        with self.assertRaisesMessage(EmptyPage, msg):
            paginator.validate_number(-1)
        # Default message.
        msg = "That page contains no results"
        with self.assertRaisesMessage(EmptyPage, msg):
            paginator.validate_number(3)

    def test_float_integer_page(self):
        paginator = Paginator([1, 2, 3], 2)
        self.assertEqual(paginator.validate_number(1.0), 1)

    def test_no_content_allow_empty_first_page(self):
        # With no content and allow_empty_first_page=True, 1 is a valid page number
        paginator = Paginator([], 2)
        self.assertEqual(paginator.validate_number(1), 1)

    def test_paginate_misc_classes(self):
        class CountContainer:
            def count(self):
                return 42

        # Paginator can be passed other objects with a count() method.
        paginator = Paginator(CountContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], list(paginator.page_range))

        # Paginator can be passed other objects that implement __len__.
        class LenContainer:
            def __len__(self):
                return 42

        paginator = Paginator(LenContainer(), 10)
        self.assertEqual(42, paginator.count)
        self.assertEqual(5, paginator.num_pages)
        self.assertEqual([1, 2, 3, 4, 5], list(paginator.page_range))

    def test_count_does_not_silence_attribute_error(self):
        class AttributeErrorContainer:
            def count(self):
                raise AttributeError("abc")

        with self.assertRaisesMessage(AttributeError, "abc"):
            Paginator(AttributeErrorContainer(), 10).count

    def test_count_does_not_silence_type_error(self):
        class TypeErrorContainer:
            def count(self):
                raise TypeError("abc")

        with self.assertRaisesMessage(TypeError, "abc"):
            Paginator(TypeErrorContainer(), 10).count

    def check_indexes(self, params, page_num, indexes):
        """
        Helper method that instantiates a Paginator object from the passed
        params and then checks that the start and end indexes of the passed
        page_num match those given as a 2-tuple in indexes.
        """
        paginator = Paginator(*params)
        if page_num == "first":
            page_num = 1
        elif page_num == "last":
            page_num = paginator.num_pages
        page = paginator.page(page_num)
        start, end = indexes
        msg = "For %s of page %s, expected %s but got %s. Paginator parameters were: %s"
        self.assertEqual(
            start,
            page.start_index(),
            msg % ("start index", page_num, start, page.start_index(), params),
        )
        self.assertEqual(
            end,
            page.end_index(),
            msg % ("end index", page_num, end, page.end_index(), params),
        )

    def test_page_indexes(self):
        """
        Paginator pages have the correct start and end indexes.
        """
        ten = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tests = (
            # Each item is 3-tuple:
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
            self.check_indexes(params, "first", first)
            self.check_indexes(params, "last", last)

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
        eleven = "abcdefghijk"
        page2 = Paginator(eleven, per_page=5, orphans=1).page(2)
        self.assertEqual(len(page2), 6)
        self.assertIn("k", page2)
        self.assertNotIn("a", page2)
        self.assertEqual("".join(page2), "fghijk")
        self.assertEqual("".join(reversed(page2)), "kjihgf")

    def test_get_page_hook(self):
        """
        A Paginator subclass can use the ``_get_page`` hook to
        return an alternative to the standard Page class.
        """
        eleven = "abcdefghijk"
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
        self.assertIsInstance(Paginator([1, 2, 3], 2).page_range, type(range(0)))

    def test_get_page(self):
        """
        Paginator.get_page() returns a valid page even with invalid page
        arguments.
        """
        paginator = Paginator([1, 2, 3], 2)
        page = paginator.get_page(1)
        self.assertEqual(page.number, 1)
        self.assertEqual(page.object_list, [1, 2])
        # An empty page returns the last page.
        self.assertEqual(paginator.get_page(3).number, 2)
        # Non-integer page returns the first page.
        self.assertEqual(paginator.get_page(None).number, 1)

    def test_get_page_empty_object_list(self):
        """Paginator.get_page() with an empty object_list."""
        paginator = Paginator([], 2)
        # An empty page returns the last page.
        self.assertEqual(paginator.get_page(1).number, 1)
        self.assertEqual(paginator.get_page(2).number, 1)
        # Non-integer page returns the first page.
        self.assertEqual(paginator.get_page(None).number, 1)

    def test_get_page_empty_object_list_and_allow_empty_first_page_false(self):
        """
        Paginator.get_page() raises EmptyPage if allow_empty_first_page=False
        and object_list is empty.
        """
        paginator = Paginator([], 2, allow_empty_first_page=False)
        with self.assertRaises(EmptyPage):
            paginator.get_page(1)

    def test_paginator_iteration(self):
        paginator = Paginator([1, 2, 3], 2)
        page_iterator = iter(paginator)
        for page, expected in enumerate(([1, 2], [3]), start=1):
            with self.subTest(page=page):
                self.assertEqual(expected, list(next(page_iterator)))

        self.assertEqual(
            [str(page) for page in iter(paginator)],
            ["<Page 1 of 2>", "<Page 2 of 2>"],
        )

    def test_get_elided_page_range(self):
        # Paginator.validate_number() must be called:
        paginator = Paginator([1, 2, 3], 2)
        with unittest.mock.patch.object(paginator, "validate_number") as mock:
            mock.assert_not_called()
            list(paginator.get_elided_page_range(2))
            mock.assert_called_with(2)

        ELLIPSIS = Paginator.ELLIPSIS

        # Range is not elided if not enough pages when using default arguments:
        paginator = Paginator(range(10 * 100), 100)
        page_range = paginator.get_elided_page_range(1)
        self.assertIsInstance(page_range, collections.abc.Generator)
        self.assertNotIn(ELLIPSIS, page_range)
        paginator = Paginator(range(10 * 100 + 1), 100)
        self.assertIsInstance(page_range, collections.abc.Generator)
        page_range = paginator.get_elided_page_range(1)
        self.assertIn(ELLIPSIS, page_range)

        # Range should be elided if enough pages when using default arguments:
        tests = [
            # on_each_side=3, on_ends=2
            (1, [1, 2, 3, 4, ELLIPSIS, 49, 50]),
            (6, [1, 2, 3, 4, 5, 6, 7, 8, 9, ELLIPSIS, 49, 50]),
            (7, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ELLIPSIS, 49, 50]),
            (8, [1, 2, ELLIPSIS, 5, 6, 7, 8, 9, 10, 11, ELLIPSIS, 49, 50]),
            (43, [1, 2, ELLIPSIS, 40, 41, 42, 43, 44, 45, 46, ELLIPSIS, 49, 50]),
            (44, [1, 2, ELLIPSIS, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (45, [1, 2, ELLIPSIS, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (50, [1, 2, ELLIPSIS, 47, 48, 49, 50]),
        ]
        paginator = Paginator(range(5000), 100)
        for number, expected in tests:
            with self.subTest(number=number):
                page_range = paginator.get_elided_page_range(number)
                self.assertIsInstance(page_range, collections.abc.Generator)
                self.assertEqual(list(page_range), expected)

        # Range is not elided if not enough pages when using custom arguments:
        tests = [
            (6, 2, 1, 1),
            (8, 1, 3, 1),
            (8, 4, 0, 1),
            (4, 1, 1, 1),
            # When on_each_side and on_ends are both <= 1 but not both == 1 it
            # is a special case where the range is not elided until an extra
            # page is added.
            (2, 0, 1, 2),
            (2, 1, 0, 2),
            (1, 0, 0, 2),
        ]
        for pages, on_each_side, on_ends, elided_after in tests:
            for offset in range(elided_after + 1):
                with self.subTest(
                    pages=pages,
                    offset=elided_after,
                    on_each_side=on_each_side,
                    on_ends=on_ends,
                ):
                    paginator = Paginator(range((pages + offset) * 100), 100)
                    page_range = paginator.get_elided_page_range(
                        1,
                        on_each_side=on_each_side,
                        on_ends=on_ends,
                    )
                    self.assertIsInstance(page_range, collections.abc.Generator)
                    if offset < elided_after:
                        self.assertNotIn(ELLIPSIS, page_range)
                    else:
                        self.assertIn(ELLIPSIS, page_range)

        # Range should be elided if enough pages when using custom arguments:
        tests = [
            # on_each_side=2, on_ends=1
            (1, 2, 1, [1, 2, 3, ELLIPSIS, 50]),
            (4, 2, 1, [1, 2, 3, 4, 5, 6, ELLIPSIS, 50]),
            (5, 2, 1, [1, 2, 3, 4, 5, 6, 7, ELLIPSIS, 50]),
            (6, 2, 1, [1, ELLIPSIS, 4, 5, 6, 7, 8, ELLIPSIS, 50]),
            (45, 2, 1, [1, ELLIPSIS, 43, 44, 45, 46, 47, ELLIPSIS, 50]),
            (46, 2, 1, [1, ELLIPSIS, 44, 45, 46, 47, 48, 49, 50]),
            (47, 2, 1, [1, ELLIPSIS, 45, 46, 47, 48, 49, 50]),
            (50, 2, 1, [1, ELLIPSIS, 48, 49, 50]),
            # on_each_side=1, on_ends=3
            (1, 1, 3, [1, 2, ELLIPSIS, 48, 49, 50]),
            (5, 1, 3, [1, 2, 3, 4, 5, 6, ELLIPSIS, 48, 49, 50]),
            (6, 1, 3, [1, 2, 3, 4, 5, 6, 7, ELLIPSIS, 48, 49, 50]),
            (7, 1, 3, [1, 2, 3, ELLIPSIS, 6, 7, 8, ELLIPSIS, 48, 49, 50]),
            (44, 1, 3, [1, 2, 3, ELLIPSIS, 43, 44, 45, ELLIPSIS, 48, 49, 50]),
            (45, 1, 3, [1, 2, 3, ELLIPSIS, 44, 45, 46, 47, 48, 49, 50]),
            (46, 1, 3, [1, 2, 3, ELLIPSIS, 45, 46, 47, 48, 49, 50]),
            (50, 1, 3, [1, 2, 3, ELLIPSIS, 49, 50]),
            # on_each_side=4, on_ends=0
            (1, 4, 0, [1, 2, 3, 4, 5, ELLIPSIS]),
            (5, 4, 0, [1, 2, 3, 4, 5, 6, 7, 8, 9, ELLIPSIS]),
            (6, 4, 0, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ELLIPSIS]),
            (7, 4, 0, [ELLIPSIS, 3, 4, 5, 6, 7, 8, 9, 10, 11, ELLIPSIS]),
            (44, 4, 0, [ELLIPSIS, 40, 41, 42, 43, 44, 45, 46, 47, 48, ELLIPSIS]),
            (45, 4, 0, [ELLIPSIS, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (46, 4, 0, [ELLIPSIS, 42, 43, 44, 45, 46, 47, 48, 49, 50]),
            (50, 4, 0, [ELLIPSIS, 46, 47, 48, 49, 50]),
            # on_each_side=0, on_ends=1
            (1, 0, 1, [1, ELLIPSIS, 50]),
            (2, 0, 1, [1, 2, ELLIPSIS, 50]),
            (3, 0, 1, [1, 2, 3, ELLIPSIS, 50]),
            (4, 0, 1, [1, ELLIPSIS, 4, ELLIPSIS, 50]),
            (47, 0, 1, [1, ELLIPSIS, 47, ELLIPSIS, 50]),
            (48, 0, 1, [1, ELLIPSIS, 48, 49, 50]),
            (49, 0, 1, [1, ELLIPSIS, 49, 50]),
            (50, 0, 1, [1, ELLIPSIS, 50]),
            # on_each_side=0, on_ends=0
            (1, 0, 0, [1, ELLIPSIS]),
            (2, 0, 0, [1, 2, ELLIPSIS]),
            (3, 0, 0, [ELLIPSIS, 3, ELLIPSIS]),
            (48, 0, 0, [ELLIPSIS, 48, ELLIPSIS]),
            (49, 0, 0, [ELLIPSIS, 49, 50]),
            (50, 0, 0, [ELLIPSIS, 50]),
        ]
        paginator = Paginator(range(5000), 100)
        for number, on_each_side, on_ends, expected in tests:
            with self.subTest(
                number=number, on_each_side=on_each_side, on_ends=on_ends
            ):
                page_range = paginator.get_elided_page_range(
                    number,
                    on_each_side=on_each_side,
                    on_ends=on_ends,
                )
                self.assertIsInstance(page_range, collections.abc.Generator)
                self.assertEqual(list(page_range), expected)


class ModelPaginationTests(TestCase):
    """
    Test pagination with Django model instances
    """

    @classmethod
    def setUpTestData(cls):
        # Prepare a list of objects for pagination.
        pub_date = datetime(2005, 7, 29)
        cls.articles = [
            Article.objects.create(headline=f"Article {x}", pub_date=pub_date)
            for x in range(1, 10)
        ]

    def test_first_page(self):
        paginator = Paginator(Article.objects.order_by("id"), 5)
        p = paginator.page(1)
        self.assertEqual("<Page 1 of 2>", str(p))
        self.assertSequenceEqual(p.object_list, self.articles[:5])
        self.assertTrue(p.has_next())
        self.assertFalse(p.has_previous())
        self.assertTrue(p.has_other_pages())
        self.assertEqual(2, p.next_page_number())
        with self.assertRaises(InvalidPage):
            p.previous_page_number()
        self.assertEqual(1, p.start_index())
        self.assertEqual(5, p.end_index())

    def test_last_page(self):
        paginator = Paginator(Article.objects.order_by("id"), 5)
        p = paginator.page(2)
        self.assertEqual("<Page 2 of 2>", str(p))
        self.assertSequenceEqual(p.object_list, self.articles[5:])
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
        paginator = Paginator(Article.objects.order_by("id"), 5)
        p = paginator.page(1)

        # object_list queryset is not evaluated by an invalid __getitem__ call.
        # (this happens from the template engine when using e.g.:
        # {% page_obj.has_previous %}).
        self.assertIsNone(p.object_list._result_cache)
        msg = "Page indices must be integers or slices, not str."
        with self.assertRaisesMessage(TypeError, msg):
            p["has_previous"]
        self.assertIsNone(p.object_list._result_cache)
        self.assertNotIsInstance(p.object_list, list)

        # Make sure slicing the Page object with numbers and slice objects work.
        self.assertEqual(p[0], self.articles[0])
        self.assertSequenceEqual(p[slice(2)], self.articles[:2])
        # After __getitem__ is called, object_list is a list
        self.assertIsInstance(p.object_list, list)

    def test_paginating_unordered_queryset_raises_warning(self):
        msg = (
            "Pagination may yield inconsistent results with an unordered "
            "object_list: <class 'pagination.models.Article'> QuerySet."
        )
        with self.assertWarnsMessage(UnorderedObjectListWarning, msg) as cm:
            Paginator(Article.objects.all(), 5)
        # The warning points at the Paginator caller (i.e. the stacklevel
        # is appropriate).
        self.assertEqual(cm.filename, __file__)

    def test_paginating_empty_queryset_does_not_warn(self):
        with warnings.catch_warnings(record=True) as recorded:
            Paginator(Article.objects.none(), 5)
        self.assertEqual(len(recorded), 0)

    def test_paginating_unordered_object_list_raises_warning(self):
        """
        Unordered object list warning with an object that has an ordered
        attribute but not a model attribute.
        """

        class ObjectList:
            ordered = False

        object_list = ObjectList()
        msg = (
            "Pagination may yield inconsistent results with an unordered "
            "object_list: {!r}.".format(object_list)
        )
        with self.assertWarnsMessage(UnorderedObjectListWarning, msg):
            Paginator(object_list, 5)
