from django.test import SimpleTestCase
from django.utils.hashable import make_hashable


class TestHashable(SimpleTestCase):
    def test_equal(self):
        tests = (
            ([], ()),
            (['a', 1], ('a', 1)),
            ({}, ()),
            ({'a'}, {'a'}),
            (frozenset({'a'}), {'a'}),
            ({'a': 1}, (('a', 1),)),
        )
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(make_hashable(value), expected)

    def test_count_equal(self):
        tests = (
            ({'a': 1, 'b': ['a', 1]}, (('a', 1), ('b', ('a', 1)))),
        )
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertCountEqual(make_hashable(value), expected)
