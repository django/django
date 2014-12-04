from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class IriencodeTests(SimpleTestCase):
    """
    Ensure iriencode keeps safe strings.
    """

    @setup({'iriencode01': '{{ url|iriencode }}'})
    def test_iriencode01(self):
        output = render('iriencode01', {'url': '?test=1&me=2'})
        self.assertEqual(output, '?test=1&amp;me=2')

    @setup({'iriencode02': '{% autoescape off %}{{ url|iriencode }}{% endautoescape %}'})
    def test_iriencode02(self):
        output = render('iriencode02', {'url': '?test=1&me=2'})
        self.assertEqual(output, '?test=1&me=2')

    @setup({'iriencode03': '{{ url|iriencode }}'})
    def test_iriencode03(self):
        output = render('iriencode03', {'url': mark_safe('?test=1&me=2')})
        self.assertEqual(output, '?test=1&me=2')

    @setup({'iriencode04': '{% autoescape off %}{{ url|iriencode }}{% endautoescape %}'})
    def test_iriencode04(self):
        output = render('iriencode04', {'url': mark_safe('?test=1&me=2')})
        self.assertEqual(output, '?test=1&me=2')
