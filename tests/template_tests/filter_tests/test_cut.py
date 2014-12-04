from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class CutTests(SimpleTestCase):

    @setup({'cut01': '{% autoescape off %}{{ a|cut:"x" }} {{ b|cut:"x" }}{% endautoescape %}'})
    def test_cut01(self):
        output = render('cut01', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "&y &amp;y")

    @setup({'cut02': '{{ a|cut:"x" }} {{ b|cut:"x" }}'})
    def test_cut02(self):
        output = render('cut02', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "&amp;y &amp;y")

    @setup({'cut03': '{% autoescape off %}{{ a|cut:"&" }} {{ b|cut:"&" }}{% endautoescape %}'})
    def test_cut03(self):
        output = render('cut03', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "xy xamp;y")

    @setup({'cut04': '{{ a|cut:"&" }} {{ b|cut:"&" }}'})
    def test_cut04(self):
        output = render('cut04', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "xy xamp;y")

    # Passing ';' to cut can break existing HTML entities, so those strings
    # are auto-escaped.
    @setup({'cut05': '{% autoescape off %}{{ a|cut:";" }} {{ b|cut:";" }}{% endautoescape %}'})
    def test_cut05(self):
        output = render('cut05', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "x&y x&ampy")

    @setup({'cut06': '{{ a|cut:";" }} {{ b|cut:";" }}'})
    def test_cut06(self):
        output = render('cut06', {"a": "x&y", "b": mark_safe("x&amp;y")})
        self.assertEqual(output, "x&amp;y x&amp;ampy")
