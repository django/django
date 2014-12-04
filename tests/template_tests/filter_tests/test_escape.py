from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class EscapeTests(SimpleTestCase):
    """
    The "escape" filter works the same whether autoescape is on or off,
    but it has no effect on strings already marked as safe.
    """

    @setup({'escape01': '{{ a|escape }} {{ b|escape }}'})
    def test_escape01(self):
        output = render('escape01', {"a": "x&y", "b": mark_safe("x&y")})
        self.assertEqual(output, "x&amp;y x&y")

    @setup({'escape02': '{% autoescape off %}{{ a|escape }} {{ b|escape }}{% endautoescape %}'})
    def test_escape02(self):
        output = render('escape02', {"a": "x&y", "b": mark_safe("x&y")})
        self.assertEqual(output, "x&amp;y x&y")

    # It is only applied once, regardless of the number of times it
    # appears in a chain.
    @setup({'escape03': '{% autoescape off %}{{ a|escape|escape }}{% endautoescape %}'})
    def test_escape03(self):
        output = render('escape03', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'escape04': '{{ a|escape|escape }}'})
    def test_escape04(self):
        output = render('escape04', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")
