import warnings

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.safestring import mark_safe

from ..utils import render, setup


class UnorderedListTests(SimpleTestCase):

    @setup({'unordered_list01': '{{ a|unordered_list }}'})
    def test_unordered_list01(self):
        output = render('unordered_list01', {'a': ['x>', ['<y']]})
        self.assertEqual(output, '\t<li>x&gt;\n\t<ul>\n\t\t<li>&lt;y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list02': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list02(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list02', {'a': ['x>', ['<y']]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list03': '{{ a|unordered_list }}'})
    def test_unordered_list03(self):
        output = render('unordered_list03', {'a': ['x>', [mark_safe('<y')]]})
        self.assertEqual(output, '\t<li>x&gt;\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list04': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list04(self):
        output = render('unordered_list04', {'a': ['x>', [mark_safe('<y')]]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list05': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list05(self):
        output = render('unordered_list05', {'a': ['x>', ['<y']]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')


class DeprecatedUnorderedListSyntaxTests(SimpleTestCase):

    @setup({'unordered_list01': '{{ a|unordered_list }}'})
    def test_unordered_list01(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list01', {'a': ['x>', [['<y', []]]]})
        self.assertEqual(output, '\t<li>x&gt;\n\t<ul>\n\t\t<li>&lt;y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list02': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list02(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list02', {'a': ['x>', [['<y', []]]]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list03': '{{ a|unordered_list }}'})
    def test_unordered_list03(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list03', {'a': ['x>', [[mark_safe('<y'), []]]]})
        self.assertEqual(output, '\t<li>x&gt;\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list04': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list04(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list04', {'a': ['x>', [[mark_safe('<y'), []]]]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')

    @setup({'unordered_list05': '{% autoescape off %}{{ a|unordered_list }}{% endautoescape %}'})
    def test_unordered_list05(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render('unordered_list05', {'a': ['x>', [['<y', []]]]})
        self.assertEqual(output, '\t<li>x>\n\t<ul>\n\t\t<li><y</li>\n\t</ul>\n\t</li>')
