from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class LjustTests(SimpleTestCase):

    @setup({'ljust01': '{% autoescape off %}.{{ a|ljust:"5" }}. .{{ b|ljust:"5" }}.{% endautoescape %}'})
    def test_ljust01(self):
        output = render('ljust01', {"a": "a&b", "b": mark_safe("a&b")})
        self.assertEqual(output, ".a&b  . .a&b  .")

    @setup({'ljust02': '.{{ a|ljust:"5" }}. .{{ b|ljust:"5" }}.'})
    def test_ljust02(self):
        output = render('ljust02', {"a": "a&b", "b": mark_safe("a&b")})
        self.assertEqual(output, ".a&amp;b  . .a&b  .")
