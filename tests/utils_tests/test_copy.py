import sys
from collections import namedtuple
from dataclasses import dataclass

from django.test import SimpleTestCase
from django.utils.copy import replace


class ReplaceTests(SimpleTestCase):
    def test_replace_namedtuple(self):
        Point = namedtuple("Point", ["x", "y"])
        p = Point(1, 2)
        p2 = replace(p, x=10)
        self.assertEqual(p2, Point(10, 2))

    def test_replace_dataclass(self):
        @dataclass
        class Color:
            r: int
            g: int
            b: int

        c = Color(255, 0, 0)
        c2 = replace(c, g=128)
        self.assertEqual(c2, Color(255, 128, 0))

    def test_replace_no_changes_returns_copy(self):
        Point = namedtuple("Point", ["x", "y"])
        p = Point(1, 2)
        p2 = replace(p)
        self.assertEqual(p, p2)

    def test_replace_preserves_type(self):
        Point = namedtuple("Point", ["x", "y"])
        p = Point(1, 2)
        p2 = replace(p, y=99)
        self.assertIsInstance(p2, Point)

    def test_replace_invalid_field(self):
        Point = namedtuple("Point", ["x", "y"])
        p = Point(1, 2)
        with self.assertRaises(TypeError):
            replace(p, z=3)

    def test_replace_unsupported_type(self):
        with self.assertRaises(TypeError):
            replace([1, 2, 3], x=10)

    def test_replace_unsupported_type_message(self):
        msg = "replace() does not support list objects"
        with self.assertRaisesMessage(TypeError, msg):
            replace([], x=1)

    def test_replace_frozen_dataclass(self):
        @dataclass(frozen=True)
        class Immutable:
            value: int

        obj = Immutable(42)
        obj2 = replace(obj, value=99)
        self.assertEqual(obj2.value, 99)
        self.assertEqual(obj.value, 42)

    if sys.version_info >= (3, 13):

        def test_delegates_to_stdlib_on_py313(self):
            import copy

            from django.utils.copy import replace as django_replace

            self.assertIs(django_replace, copy.replace)
