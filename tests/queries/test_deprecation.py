from contextlib import contextmanager

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db.models.query_utils import InvalidQuery
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango40Warning


class InvalidQueryTests(SimpleTestCase):
    @contextmanager
    def assert_warns(self):
        msg = (
            'The InvalidQuery exception class is deprecated. Use '
            'FieldDoesNotExist or FieldError instead.'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            yield

    def test_type(self):
        self.assertIsInstance(InvalidQuery(), InvalidQuery)

    def test_isinstance(self):
        for exception in (FieldError, FieldDoesNotExist):
            with self.assert_warns(), self.subTest(exception.__name__):
                self.assertIsInstance(exception(), InvalidQuery)

    def test_issubclass(self):
        for exception in (FieldError, FieldDoesNotExist, InvalidQuery):
            with self.assert_warns(), self.subTest(exception.__name__):
                self.assertIs(issubclass(exception, InvalidQuery), True)
