from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class RjustTests(SimpleTestCase):

    @setup({'rjust01': '{% autoescape off %}.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.{% endautoescape %}'})
    def test_rjust01(self):
        output = render('rjust01', {"a": "a&b", "b": mark_safe("a&b")})
        self.assertEqual(output, ".  a&b. .  a&b.")

    @setup({'rjust02': '.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.'})
    def test_rjust02(self):
        output = render('rjust02', {"a": "a&b", "b": mark_safe("a&b")})
        self.assertEqual(output, ".  a&amp;b. .  a&b.")
