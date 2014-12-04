from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class WordcountTests(SimpleTestCase):

    @setup({'wordcount01': '{% autoescape off %}{{ a|wordcount }} {{ b|wordcount }}{% endautoescape %}'})
    def test_wordcount01(self):
        output = render('wordcount01', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, '3 3')

    @setup({'wordcount02': '{{ a|wordcount }} {{ b|wordcount }}'})
    def test_wordcount02(self):
        output = render('wordcount02', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, '3 3')
