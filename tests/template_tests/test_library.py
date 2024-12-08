import functools

from django.template import Library
from django.template.base import Node
from django.test import SimpleTestCase


class FilterRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.library = Library()

    def test_filter(self):
        @self.library.filter
        def func():
            return ""

        self.assertEqual(self.library.filters["func"], func)

    def test_filter_parens(self):
        @self.library.filter()
        def func():
            return ""

        self.assertEqual(self.library.filters["func"], func)

    def test_filter_name_arg(self):
        @self.library.filter("name")
        def func():
            return ""

        self.assertEqual(self.library.filters["name"], func)

    def test_filter_name_kwarg(self):
        @self.library.filter(name="name")
        def func():
            return ""

        self.assertEqual(self.library.filters["name"], func)

    def test_filter_call(self):
        def func():
            return ""

        self.library.filter("name", func)
        self.assertEqual(self.library.filters["name"], func)

    def test_filter_invalid(self):
        msg = "Unsupported arguments to Library.filter: (None, '')"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.filter(None, "")


class InclusionTagRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.library = Library()

    def test_inclusion_tag(self):
        @self.library.inclusion_tag("template.html")
        def func():
            return ""

        self.assertIn("func", self.library.tags)

    def test_inclusion_tag_name(self):
        @self.library.inclusion_tag("template.html", name="name")
        def func():
            return ""

        self.assertIn("name", self.library.tags)

    def test_inclusion_tag_wrapped(self):
        @self.library.inclusion_tag("template.html")
        @functools.lru_cache(maxsize=32)
        def func():
            return ""

        func_wrapped = self.library.tags["func"].__wrapped__
        self.assertIs(func_wrapped, func)
        self.assertTrue(hasattr(func_wrapped, "cache_info"))


class SimpleTagRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.library = Library()

    def test_simple_tag(self):
        @self.library.simple_tag
        def func():
            return ""

        self.assertIn("func", self.library.tags)

    def test_simple_tag_parens(self):
        @self.library.simple_tag()
        def func():
            return ""

        self.assertIn("func", self.library.tags)

    def test_simple_tag_name_kwarg(self):
        @self.library.simple_tag(name="name")
        def func():
            return ""

        self.assertIn("name", self.library.tags)

    def test_simple_tag_invalid(self):
        msg = "Invalid arguments provided to simple_tag"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.simple_tag("invalid")

    def test_simple_tag_wrapped(self):
        @self.library.simple_tag
        @functools.lru_cache(maxsize=32)
        def func():
            return ""

        func_wrapped = self.library.tags["func"].__wrapped__
        self.assertIs(func_wrapped, func)
        self.assertTrue(hasattr(func_wrapped, "cache_info"))


class SimpleBlockTagRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.library = Library()

    def test_simple_block_tag(self):
        @self.library.simple_block_tag
        def func(content):
            return content

        self.assertIn("func", self.library.tags)

    def test_simple_block_tag_parens(self):
        @self.library.simple_tag()
        def func(content):
            return content

        self.assertIn("func", self.library.tags)

    def test_simple_block_tag_name_kwarg(self):
        @self.library.simple_block_tag(name="name")
        def func(content):
            return content

        self.assertIn("name", self.library.tags)

    def test_simple_block_tag_invalid(self):
        msg = "Invalid arguments provided to simple_block_tag"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.simple_block_tag("invalid")

    def test_simple_tag_wrapped(self):
        @self.library.simple_block_tag
        @functools.lru_cache(maxsize=32)
        def func(content):
            return content

        func_wrapped = self.library.tags["func"].__wrapped__
        self.assertIs(func_wrapped, func)
        self.assertTrue(hasattr(func_wrapped, "cache_info"))


class TagRegistrationTests(SimpleTestCase):
    def setUp(self):
        self.library = Library()

    def test_tag(self):
        @self.library.tag
        def func(parser, token):
            return Node()

        self.assertEqual(self.library.tags["func"], func)

    def test_tag_parens(self):
        @self.library.tag()
        def func(parser, token):
            return Node()

        self.assertEqual(self.library.tags["func"], func)

    def test_tag_name_arg(self):
        @self.library.tag("name")
        def func(parser, token):
            return Node()

        self.assertEqual(self.library.tags["name"], func)

    def test_tag_name_kwarg(self):
        @self.library.tag(name="name")
        def func(parser, token):
            return Node()

        self.assertEqual(self.library.tags["name"], func)

    def test_tag_call(self):
        def func(parser, token):
            return Node()

        self.library.tag("name", func)
        self.assertEqual(self.library.tags["name"], func)

    def test_tag_invalid(self):
        msg = "Unsupported arguments to Library.tag: (None, '')"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.tag(None, "")
