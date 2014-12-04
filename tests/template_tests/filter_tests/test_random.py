from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class RandomTests(SimpleTestCase):

    @setup({'random01': '{{ a|random }} {{ b|random }}'})
    def test_random01(self):
        output = render('random01', {'a': ['a&b', 'a&b'], 'b': [mark_safe('a&b'), mark_safe('a&b')]})
        self.assertEqual(output, 'a&amp;b a&b')

    @setup({'random02': '{% autoescape off %}{{ a|random }} {{ b|random }}{% endautoescape %}'})
    def test_random02(self):
        output = render('random02', {'a': ['a&b', 'a&b'], 'b': [mark_safe('a&b'), mark_safe('a&b')]})
        self.assertEqual(output, 'a&b a&b')
