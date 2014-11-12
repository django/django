from django.template.base import TemplateSyntaxError
from django.template.loader import get_template
from django.test import TestCase

from .utils import render, setup


class SimpleTagTests(TestCase):

    @setup({'simpletag-renamed01': '{% load custom %}{% minusone 7 %}'})
    def test_simpletag_renamed01(self):
        output = render('simpletag-renamed01')
        self.assertEqual(output, '6')

    @setup({'simpletag-renamed02': '{% load custom %}{% minustwo 7 %}'})
    def test_simpletag_renamed02(self):
        output = render('simpletag-renamed02')
        self.assertEqual(output, '5')

    @setup({'simpletag-renamed03': '{% load custom %}{% minustwo_overridden_name 7 %}'})
    def test_simpletag_renamed03(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('simpletag-renamed03')
