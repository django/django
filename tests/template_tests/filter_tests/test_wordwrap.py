from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class WordwrapTests(SimpleTestCase):

    @setup({'wordwrap01':
        '{% autoescape off %}{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}{% endautoescape %}'})
    def test_wordwrap01(self):
        output = render('wordwrap01', {'a': 'a & b', 'b': mark_safe('a & b')})
        self.assertEqual(output, 'a &\nb a &\nb')

    @setup({'wordwrap02': '{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}'})
    def test_wordwrap02(self):
        output = render('wordwrap02', {'a': 'a & b', 'b': mark_safe('a & b')})
        self.assertEqual(output, 'a &amp;\nb a &\nb')
