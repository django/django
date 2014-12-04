from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class StringformatTests(SimpleTestCase):
    """
    Notice that escaping is applied *after* any filters, so the string
    formatting here only needs to deal with pre-escaped characters.
    """

    @setup({'stringformat01':
        '{% autoescape off %}.{{ a|stringformat:"5s" }}. .{{ b|stringformat:"5s" }}.{% endautoescape %}'})
    def test_stringformat01(self):
        output = render('stringformat01', {'a': 'a<b', 'b': mark_safe('a<b')})
        self.assertEqual(output, '.  a<b. .  a<b.')

    @setup({'stringformat02': '.{{ a|stringformat:"5s" }}. .{{ b|stringformat:"5s" }}.'})
    def test_stringformat02(self):
        output = render('stringformat02', {'a': 'a<b', 'b': mark_safe('a<b')})
        self.assertEqual(output, '.  a&lt;b. .  a<b.')
