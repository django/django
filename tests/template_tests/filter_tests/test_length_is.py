from django.template.defaultfilters import length_is
from django.test import SimpleTestCase

from ..utils import setup


class LengthIsTests(SimpleTestCase):

    @setup({'length_is01': '{% if some_list|length_is:"4" %}Four{% endif %}'})
    def test_length_is01(self):
        output = self.engine.render_to_string('length_is01', {'some_list': ['4', None, True, {}]})
        self.assertEqual(output, 'Four')

    @setup({'length_is02': '{% if some_list|length_is:"4" %}Four{% else %}Not Four{% endif %}'})
    def test_length_is02(self):
        output = self.engine.render_to_string('length_is02', {'some_list': ['4', None, True, {}, 17]})
        self.assertEqual(output, 'Not Four')

    @setup({'length_is03': '{% if mystring|length_is:"4" %}Four{% endif %}'})
    def test_length_is03(self):
        output = self.engine.render_to_string('length_is03', {'mystring': 'word'})
        self.assertEqual(output, 'Four')

    @setup({'length_is04': '{% if mystring|length_is:"4" %}Four{% else %}Not Four{% endif %}'})
    def test_length_is04(self):
        output = self.engine.render_to_string('length_is04', {'mystring': 'Python'})
        self.assertEqual(output, 'Not Four')

    @setup({'length_is05': '{% if mystring|length_is:"4" %}Four{% else %}Not Four{% endif %}'})
    def test_length_is05(self):
        output = self.engine.render_to_string('length_is05', {'mystring': ''})
        self.assertEqual(output, 'Not Four')

    @setup({'length_is06': '{% with var|length as my_length %}{{ my_length }}{% endwith %}'})
    def test_length_is06(self):
        output = self.engine.render_to_string('length_is06', {'var': 'django'})
        self.assertEqual(output, '6')

    # Boolean return value from length_is should not be coerced to a string
    @setup({'length_is07': '{% if "X"|length_is:0 %}Length is 0{% else %}Length not 0{% endif %}'})
    def test_length_is07(self):
        output = self.engine.render_to_string('length_is07', {})
        self.assertEqual(output, 'Length not 0')

    @setup({'length_is08': '{% if "X"|length_is:1 %}Length is 1{% else %}Length not 1{% endif %}'})
    def test_length_is08(self):
        output = self.engine.render_to_string('length_is08', {})
        self.assertEqual(output, 'Length is 1')

    # Invalid uses that should fail silently.
    @setup({'length_is09': '{{ var|length_is:"fish" }}'})
    def test_length_is09(self):
        output = self.engine.render_to_string('length_is09', {'var': 'django'})
        self.assertEqual(output, '')

    @setup({'length_is10': '{{ int|length_is:"1" }}'})
    def test_length_is10(self):
        output = self.engine.render_to_string('length_is10', {'int': 7})
        self.assertEqual(output, '')

    @setup({'length_is11': '{{ none|length_is:"1" }}'})
    def test_length_is11(self):
        output = self.engine.render_to_string('length_is11', {'none': None})
        self.assertEqual(output, '')


class FunctionTests(SimpleTestCase):

    def test_empty_list(self):
        self.assertIs(length_is([], 0), True)
        self.assertIs(length_is([], 1), False)

    def test_string(self):
        self.assertIs(length_is('a', 1), True)
        self.assertIs(length_is('a', 10), False)
