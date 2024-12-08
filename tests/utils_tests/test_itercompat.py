# RemovedInDjango60Warning: Remove this entire module.

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.itercompat import is_iterable


class TestIterCompat(SimpleTestCase):
    def test_is_iterable_deprecation(self):
        msg = (
            "django.utils.itercompat.is_iterable() is deprecated. "
            "Use isinstance(..., collections.abc.Iterable) instead."
        )
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg) as ctx:
            is_iterable([])
        self.assertEqual(ctx.filename, __file__)
