from django.template.defaultfilters import make_list
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class MakeListTests(SimpleTestCase):
    """
    The make_list filter can destroy existing escaping, so the results are
    escaped.
    """

    @setup({'make_list01': '{% autoescape off %}{{ a|make_list }}{% endautoescape %}'})
    def test_make_list01(self):
        output = self.engine.render_to_string('make_list01', {"a": mark_safe("&")})
        self.assertEqual(output, "['&']")

    @setup({'make_list02': '{{ a|make_list }}'})
    def test_make_list02(self):
        output = self.engine.render_to_string('make_list02', {"a": mark_safe("&")})
        self.assertEqual(output, '[&#x27;&amp;&#x27;]')

    @setup({'make_list03': '{% autoescape off %}{{ a|make_list|stringformat:"s"|safe }}{% endautoescape %}'})
    def test_make_list03(self):
        output = self.engine.render_to_string('make_list03', {"a": mark_safe("&")})
        self.assertEqual(output, "['&']")

    @setup({'make_list04': '{{ a|make_list|stringformat:"s"|safe }}'})
    def test_make_list04(self):
        output = self.engine.render_to_string('make_list04', {"a": mark_safe("&")})
        self.assertEqual(output, "['&']")


class FunctionTests(SimpleTestCase):

    def test_string(self):
        self.assertEqual(make_list('abc'), ['a', 'b', 'c'])

    def test_integer(self):
        self.assertEqual(make_list(1234), ['1', '2', '3', '4'])
