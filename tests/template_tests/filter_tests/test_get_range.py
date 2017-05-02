from django.template.defaultfilters import get_range
from django.test import SimpleTestCase
from django.test.utils import str_prefix
from django.utils.safestring import mark_safe

from ..utils import setup


class FunctionTests(SimpleTestCase):

    def test_string(self):
        self.assertEqual(get_range('5'), [0, 1, 2, 3, 4])

    def test_integer(self):
        self.assertEqual(get_range(5), [0, 1, 2, 3, 4])
