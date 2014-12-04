from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class FloatformatTests(SimpleTestCase):

    @setup({'floatformat01':
        '{% autoescape off %}{{ a|floatformat }} {{ b|floatformat }}{% endautoescape %}'})
    def test_floatformat01(self):
        output = render('floatformat01', {"a": "1.42", "b": mark_safe("1.42")})
        self.assertEqual(output, "1.4 1.4")

    @setup({'floatformat02': '{{ a|floatformat }} {{ b|floatformat }}'})
    def test_floatformat02(self):
        output = render('floatformat02', {"a": "1.42", "b": mark_safe("1.42")})
        self.assertEqual(output, "1.4 1.4")
