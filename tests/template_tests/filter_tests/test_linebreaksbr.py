from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class LinebreaksbrTests(SimpleTestCase):
    """
    The contents in "linebreaksbr" are escaped according to the current
    autoescape setting.
    """

    @setup({'linebreaksbr01': '{{ a|linebreaksbr }} {{ b|linebreaksbr }}'})
    def test_linebreaksbr01(self):
        output = render('linebreaksbr01', {"a": "x&\ny", "b": mark_safe("x&\ny")})
        self.assertEqual(output, "x&amp;<br />y x&<br />y")

    @setup({'linebreaksbr02':
        '{% autoescape off %}{{ a|linebreaksbr }} {{ b|linebreaksbr }}{% endautoescape %}'})
    def test_linebreaksbr02(self):
        output = render('linebreaksbr02', {"a": "x&\ny", "b": mark_safe("x&\ny")})
        self.assertEqual(output, "x&<br />y x&<br />y")
