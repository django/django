from django.template.defaultfilters import linebreaks_filter
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class LinebreaksTests(SimpleTestCase):
    """
    The contents in "linebreaks" are escaped according to the current
    autoescape setting.
    """

    @setup({'linebreaks01': '{{ a|linebreaks }} {{ b|linebreaks }}'})
    def test_linebreaks01(self):
        output = render('linebreaks01', {"a": "x&\ny", "b": mark_safe("x&\ny")})
        self.assertEqual(output, "<p>x&amp;<br />y</p> <p>x&<br />y</p>")

    @setup({'linebreaks02':
        '{% autoescape off %}{{ a|linebreaks }} {{ b|linebreaks }}{% endautoescape %}'})
    def test_linebreaks02(self):
        output = render('linebreaks02', {"a": "x&\ny", "b": mark_safe("x&\ny")})
        self.assertEqual(output, "<p>x&<br />y</p> <p>x&<br />y</p>")


class FunctionTests(SimpleTestCase):

    def test_line(self):
        self.assertEqual(linebreaks_filter('line 1'), '<p>line 1</p>')

    def test_newline(self):
        self.assertEqual(linebreaks_filter('line 1\nline 2'), '<p>line 1<br />line 2</p>')

    def test_carriage(self):
        self.assertEqual(linebreaks_filter('line 1\rline 2'), '<p>line 1<br />line 2</p>')

    def test_carriage_newline(self):
        self.assertEqual(linebreaks_filter('line 1\r\nline 2'), '<p>line 1<br />line 2</p>')

    def test_non_string_input(self):
        self.assertEqual(linebreaks_filter(123), '<p>123</p>')
