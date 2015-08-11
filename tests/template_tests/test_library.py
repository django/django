from django.template import Library
from django.template.base import Node
from django.test import TestCase


class FilterRegistrationTests(TestCase):

    def setUp(self):
        self.library = Library()

    def test_filter(self):
        @self.library.filter
        def func():
            return ''
        self.assertEqual(self.library.filters['func'], func)

    def test_filter_parens(self):
        @self.library.filter()
        def func():
            return ''
        self.assertEqual(self.library.filters['func'], func)

    def test_filter_name_arg(self):
        @self.library.filter('name')
        def func():
            return ''
        self.assertEqual(self.library.filters['name'], func)

    def test_filter_name_kwarg(self):
        @self.library.filter(name='name')
        def func():
            return ''
        self.assertEqual(self.library.filters['name'], func)

    def test_filter_call(self):
        def func():
            return ''
        self.library.filter('name', func)
        self.assertEqual(self.library.filters['name'], func)

    def test_filter_invalid(self):
        msg = "Unsupported arguments to Library.filter: (None, '')"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.filter(None, '')


class InclusionTagRegistrationTests(TestCase):

    def setUp(self):
        self.library = Library()

    def test_inclusion_tag(self):
        @self.library.inclusion_tag('template.html')
        def func():
            return ''
        self.assertIn('func', self.library.tags)

    def test_inclusion_tag_name(self):
        @self.library.inclusion_tag('template.html', name='name')
        def func():
            return ''
        self.assertIn('name', self.library.tags)


class SimpleTagRegistrationTests(TestCase):

    def setUp(self):
        self.library = Library()

    def test_simple_tag(self):
        @self.library.simple_tag
        def func():
            return ''
        self.assertIn('func', self.library.tags)

    def test_simple_tag_parens(self):
        @self.library.simple_tag()
        def func():
            return ''
        self.assertIn('func', self.library.tags)

    def test_simple_tag_name_kwarg(self):
        @self.library.simple_tag(name='name')
        def func():
            return ''
        self.assertIn('name', self.library.tags)

    def test_simple_tag_invalid(self):
        msg = "Invalid arguments provided to simple_tag"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.simple_tag('invalid')


class TagRegistrationTests(TestCase):

    def setUp(self):
        self.library = Library()

    def test_tag(self):
        @self.library.tag
        def func(parser, token):
            return Node()
        self.assertEqual(self.library.tags['func'], func)

    def test_tag_parens(self):
        @self.library.tag()
        def func(parser, token):
            return Node()
        self.assertEqual(self.library.tags['func'], func)

    def test_tag_name_arg(self):
        @self.library.tag('name')
        def func(parser, token):
            return Node()
        self.assertEqual(self.library.tags['name'], func)

    def test_tag_name_kwarg(self):
        @self.library.tag(name='name')
        def func(parser, token):
            return Node()
        self.assertEqual(self.library.tags['name'], func)

    def test_tag_call(self):
        def func(parser, token):
            return Node()
        self.library.tag('name', func)
        self.assertEqual(self.library.tags['name'], func)

    def test_tag_invalid(self):
        msg = "Unsupported arguments to Library.tag: (None, '')"
        with self.assertRaisesMessage(ValueError, msg):
            self.library.tag(None, '')
