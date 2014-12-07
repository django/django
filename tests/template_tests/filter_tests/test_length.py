from django.template.defaultfilters import length
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class LengthTests(SimpleTestCase):

    @setup({'length01': '{{ list|length }}'})
    def test_length01(self):
        output = self.engine.render_to_string('length01', {'list': ['4', None, True, {}]})
        self.assertEqual(output, '4')

    @setup({'length02': '{{ list|length }}'})
    def test_length02(self):
        output = self.engine.render_to_string('length02', {'list': []})
        self.assertEqual(output, '0')

    @setup({'length03': '{{ string|length }}'})
    def test_length03(self):
        output = self.engine.render_to_string('length03', {'string': ''})
        self.assertEqual(output, '0')

    @setup({'length04': '{{ string|length }}'})
    def test_length04(self):
        output = self.engine.render_to_string('length04', {'string': 'django'})
        self.assertEqual(output, '6')

    @setup({'length05': '{% if string|length == 6 %}Pass{% endif %}'})
    def test_length05(self):
        output = self.engine.render_to_string('length05', {'string': mark_safe('django')})
        self.assertEqual(output, 'Pass')

    # Invalid uses that should fail silently.
    @setup({'length06': '{{ int|length }}'})
    def test_length06(self):
        output = self.engine.render_to_string('length06', {'int': 7})
        self.assertEqual(output, '0')

    @setup({'length07': '{{ None|length }}'})
    def test_length07(self):
        output = self.engine.render_to_string('length07', {'None': None})
        self.assertEqual(output, '0')


class FunctionTests(SimpleTestCase):

    def test_string(self):
        self.assertEqual(length('1234'), 4)

    def test_safestring(self):
        self.assertEqual(length(mark_safe('1234')), 4)

    def test_list(self):
        self.assertEqual(length([1, 2, 3, 4]), 4)
