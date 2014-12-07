from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class SimpleTagTests(SimpleTestCase):

    @setup({'simpletag-renamed01': '{% load custom %}{% minusone 7 %}'})
    def test_simpletag_renamed01(self):
        output = self.engine.render_to_string('simpletag-renamed01')
        self.assertEqual(output, '6')

    @setup({'simpletag-renamed02': '{% load custom %}{% minustwo 7 %}'})
    def test_simpletag_renamed02(self):
        output = self.engine.render_to_string('simpletag-renamed02')
        self.assertEqual(output, '5')

    @setup({'simpletag-renamed03': '{% load custom %}{% minustwo_overridden_name 7 %}'})
    def test_simpletag_renamed03(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('simpletag-renamed03')
