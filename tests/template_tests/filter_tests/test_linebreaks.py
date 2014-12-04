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
