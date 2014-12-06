from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class SlugifyTests(SimpleTestCase):
    """
    Running slugify on a pre-escaped string leads to odd behavior,
    but the result is still safe.
    """

    @setup({'slugify01': '{% autoescape off %}{{ a|slugify }} {{ b|slugify }}{% endautoescape %}'})
    def test_slugify01(self):
        output = render('slugify01', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'a-b a-amp-b')

    @setup({'slugify02': '{{ a|slugify }} {{ b|slugify }}'})
    def test_slugify02(self):
        output = render('slugify02', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'a-b a-amp-b')
