from django.test import SimpleTestCase
from django.utils.hashable import make_hashable


class TestHashable(SimpleTestCase):
    def test_equal(self):
        tests = (
            ([], ()),
            (['a', 1], ('a', 1)),
            ({}, ()),
            ({'a'}, ('a',)),
            (frozenset({'a'}), {'a'}),
            ({'a': 1}, (('a', 1),)),
            (('a', ['b', 1]), ('a', ('b', 1))),
            (('a', {'b': 1}), ('a', (('b', 1),))),
        )
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(make_hashable(value), expected)

    def test_count_equal(self):
        tests = (
            ({'a': 1, 'b': ['a', 1]}, (('a', 1), ('b', ('a', 1)))),
            ({'a': 1, 'b': ('a', [1, 2])}, (('a', 1), ('b', ('a', (1, 2))))),
        )
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertCountEqual(make_hashable(value), expected)

    def test_unhashable(self):
        class Unhashable:
            __hash__ = None

        with self.assertRaisesMessage(TypeError, "unhashable type: 'Unhashable'"):
            make_hashable(Unhashable())
