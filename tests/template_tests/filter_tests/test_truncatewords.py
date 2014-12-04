from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class TruncatewordsTests(SimpleTestCase):

    @setup({'truncatewords01':
        '{% autoescape off %}{{ a|truncatewords:"2" }} {{ b|truncatewords:"2"}}{% endautoescape %}'})
    def test_truncatewords01(self):
        output = render('truncatewords01', {'a': 'alpha & bravo', 'b': mark_safe('alpha &amp; bravo')})
        self.assertEqual(output, 'alpha & ... alpha &amp; ...')

    @setup({'truncatewords02': '{{ a|truncatewords:"2" }} {{ b|truncatewords:"2"}}'})
    def test_truncatewords02(self):
        output = render('truncatewords02', {'a': 'alpha & bravo', 'b': mark_safe('alpha &amp; bravo')})
        self.assertEqual(output, 'alpha &amp; ... alpha &amp; ...')
