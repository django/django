from django.test import SimpleTestCase

from ..utils import render, setup, SafeClass, UnsafeClass


class AutoescapeStringfilterTests(SimpleTestCase):
    """
    Filters decorated with stringfilter still respect is_safe.
    """

    @setup({'autoescape-stringfilter01': '{{ unsafe|capfirst }}'})
    def test_autoescape_stringfilter01(self):
        output = render('autoescape-stringfilter01', {'unsafe': UnsafeClass()})
        self.assertEqual(output, 'You &amp; me')

    @setup({'autoescape-stringfilter02': '{% autoescape off %}{{ unsafe|capfirst }}{% endautoescape %}'})
    def test_autoescape_stringfilter02(self):
        output = render('autoescape-stringfilter02', {'unsafe': UnsafeClass()})
        self.assertEqual(output, 'You & me')

    @setup({'autoescape-stringfilter03': '{{ safe|capfirst }}'})
    def test_autoescape_stringfilter03(self):
        output = render('autoescape-stringfilter03', {'safe': SafeClass()})
        self.assertEqual(output, 'You &gt; me')

    @setup({'autoescape-stringfilter04': '{% autoescape off %}{{ safe|capfirst }}{% endautoescape %}'})
    def test_autoescape_stringfilter04(self):
        output = render('autoescape-stringfilter04', {'safe': SafeClass()})
        self.assertEqual(output, 'You &gt; me')
