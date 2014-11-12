from django.template.base import TemplateSyntaxError
from django.template.loader import get_template
from django.test import TestCase

from .utils import render, setup


class FilterTagTests(TestCase):

    @setup({'filter01': '{% filter upper %}{% endfilter %}'})
    def test_filter01(self):
        output = render('filter01')
        self.assertEqual(output, '')

    @setup({'filter02': '{% filter upper %}django{% endfilter %}'})
    def test_filter02(self):
        output = render('filter02')
        self.assertEqual(output, 'DJANGO')

    @setup({'filter03': '{% filter upper|lower %}django{% endfilter %}'})
    def test_filter03(self):
        output = render('filter03')
        self.assertEqual(output, 'django')

    @setup({'filter04': '{% filter cut:remove %}djangospam{% endfilter %}'})
    def test_filter04(self):
        output = render('filter04', {'remove': 'spam'})
        self.assertEqual(output, 'django')

    @setup({'filter05': '{% filter safe %}fail{% endfilter %}'})
    def test_filter05(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('filter05')

    @setup({'filter05bis': '{% filter upper|safe %}fail{% endfilter %}'})
    def test_filter05bis(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('filter05bis')

    @setup({'filter06': '{% filter escape %}fail{% endfilter %}'})
    def test_filter06(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('filter06')

    @setup({'filter06bis': '{% filter upper|escape %}fail{% endfilter %}'})
    def test_filter06bis(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('filter06bis')
