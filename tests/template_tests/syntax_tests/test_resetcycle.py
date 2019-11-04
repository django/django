from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class ResetCycleTagTests(SimpleTestCase):

    @setup({'resetcycle01': "{% resetcycle %}"})
    def test_resetcycle01(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "No cycles in template."):
            self.engine.get_template('resetcycle01')

    @setup({'resetcycle02': "{% resetcycle undefinedcycle %}"})
    def test_resetcycle02(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Named cycle 'undefinedcycle' does not exist."):
            self.engine.get_template('resetcycle02')

    @setup({'resetcycle03': "{% cycle 'a' 'b' %}{% resetcycle undefinedcycle %}"})
    def test_resetcycle03(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Named cycle 'undefinedcycle' does not exist."):
            self.engine.get_template('resetcycle03')

    @setup({'resetcycle04': "{% cycle 'a' 'b' as ab %}{% resetcycle undefinedcycle %}"})
    def test_resetcycle04(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Named cycle 'undefinedcycle' does not exist."):
            self.engine.get_template('resetcycle04')

    @setup({'resetcycle05': "{% for i in test %}{% cycle 'a' 'b' %}{% resetcycle %}{% endfor %}"})
    def test_resetcycle05(self):
        output = self.engine.render_to_string('resetcycle05', {'test': list(range(5))})
        self.assertEqual(output, 'aaaaa')

    @setup({'resetcycle06': "{% cycle 'a' 'b' 'c' as abc %}"
                            "{% for i in test %}"
                            "{% cycle abc %}"
                            "{% cycle '-' '+' %}"
                            "{% resetcycle %}"
                            "{% endfor %}"})
    def test_resetcycle06(self):
        output = self.engine.render_to_string('resetcycle06', {'test': list(range(5))})
        self.assertEqual(output, 'ab-c-a-b-c-')

    @setup({'resetcycle07': "{% cycle 'a' 'b' 'c' as abc %}"
                            "{% for i in test %}"
                            "{% resetcycle abc %}"
                            "{% cycle abc %}"
                            "{% cycle '-' '+' %}"
                            "{% endfor %}"})
    def test_resetcycle07(self):
        output = self.engine.render_to_string('resetcycle07', {'test': list(range(5))})
        self.assertEqual(output, 'aa-a+a-a+a-')

    @setup({'resetcycle08': "{% for i in outer %}"
                            "{% for j in inner %}"
                            "{% cycle 'a' 'b' %}"
                            "{% endfor %}"
                            "{% resetcycle %}"
                            "{% endfor %}"})
    def test_resetcycle08(self):
        output = self.engine.render_to_string('resetcycle08', {'outer': list(range(2)), 'inner': list(range(3))})
        self.assertEqual(output, 'abaaba')

    @setup({'resetcycle09': "{% for i in outer %}"
                            "{% cycle 'a' 'b' %}"
                            "{% for j in inner %}"
                            "{% cycle 'X' 'Y' %}"
                            "{% endfor %}"
                            "{% resetcycle %}"
                            "{% endfor %}"})
    def test_resetcycle09(self):
        output = self.engine.render_to_string('resetcycle09', {'outer': list(range(2)), 'inner': list(range(3))})
        self.assertEqual(output, 'aXYXbXYX')

    @setup({'resetcycle10': "{% for i in test %}"
                            "{% cycle 'X' 'Y' 'Z' as XYZ %}"
                            "{% cycle 'a' 'b' 'c' as abc %}"
                            "{% ifequal i 1 %}"
                            "{% resetcycle abc %}"
                            "{% endifequal %}"
                            "{% endfor %}"})
    def test_resetcycle10(self):
        output = self.engine.render_to_string('resetcycle10', {'test': list(range(5))})
        self.assertEqual(output, 'XaYbZaXbYc')

    @setup({'resetcycle11': "{% for i in test %}"
                            "{% cycle 'X' 'Y' 'Z' as XYZ %}"
                            "{% cycle 'a' 'b' 'c' as abc %}"
                            "{% ifequal i 1 %}"
                            "{% resetcycle XYZ %}"
                            "{% endifequal %}"
                            "{% endfor %}"})
    def test_resetcycle11(self):
        output = self.engine.render_to_string('resetcycle11', {'test': list(range(5))})
        self.assertEqual(output, 'XaYbXcYaZb')
