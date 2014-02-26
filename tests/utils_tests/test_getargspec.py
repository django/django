from unittest import skipIf

from django.utils import six, inspect
from django.test import SimpleTestCase

@skipIf(six.PY2, 'for Python 3 only')
class GetargspecPy3TestCase(SimpleTestCase):
    def test_getargspec(self):
        """
        Test that getargspec() correctly parse the functions
        with annotations and keywords-only arguments
        """

        from .py3_handlers import (handler_with_kwargs_only,
                                   handler_with_annotations,
                                   handler_simple)

        args = inspect.getargspec(handler_with_kwargs_only)
        self.assertEqual(args, inspect.ArgSpec([], None, 'kwargs', None))

        args = inspect.getargspec(handler_with_annotations)
        self.assertEqual(args, inspect.ArgSpec(['sender', 'instance'], None,
                                               'kwargs', None))

        args = inspect.getargspec(handler_simple)
        self.assertEqual(args, inspect.ArgSpec(['sender', 'instance'], None,
                                               'kwargs', (None,)))

@skipIf(six.PY3, 'for Python 2 only')
class GetargspecPy2TestCase(SimpleTestCase):
    def test_getargspec(self):
        """
        Test that getargspec() correctly parse any functions
        """

        from .py2_handlers import handler_simple

        args = inspect.getargspec(handler_simple)
        self.assertEqual(args, inspect.ArgSpec(['sender', 'instance'], None,
                                               'kwargs', defaults=(None,)))