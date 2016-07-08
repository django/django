from django.template.defaultfilters import escape
from django.test import SimpleTestCase, ignore_warnings
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import Promise, lazy
from django.utils.safestring import mark_safe

from ..utils import setup


class EscapeTests(SimpleTestCase):
    """
    The "escape" filter works the same whether autoescape is on or off,
    but it has no effect on strings already marked as safe.
    """

    @setup({'escape01': '{{ a|escape }} {{ b|escape }}'})
    def test_escape01(self):
        output = self.engine.render_to_string('escape01', {"a": "x&y", "b": mark_safe("x&y")})
        self.assertEqual(output, "x&amp;y x&y")

    @setup({'escape02': '{% autoescape off %}{{ a|escape }} {{ b|escape }}{% endautoescape %}'})
    def test_escape02(self):
        output = self.engine.render_to_string('escape02', {"a": "x&y", "b": mark_safe("x&y")})
        self.assertEqual(output, "x&amp;y x&y")

    # It is only applied once, regardless of the number of times it
    # appears in a chain (to be changed in Django 2.0).
    @ignore_warnings(category=RemovedInDjango20Warning)
    @setup({'escape03': '{% autoescape off %}{{ a|escape|escape }}{% endautoescape %}'})
    def test_escape03(self):
        output = self.engine.render_to_string('escape03', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @ignore_warnings(category=RemovedInDjango20Warning)
    @setup({'escape04': '{{ a|escape|escape }}'})
    def test_escape04(self):
        output = self.engine.render_to_string('escape04', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    def test_escape_lazy_string(self):
        add_html = lazy(lambda string: string + 'special characters > here', six.text_type)
        escaped = escape(add_html('<some html & '))
        self.assertIsInstance(escaped, Promise)
        self.assertEqual(escaped, '&lt;some html &amp; special characters &gt; here')


class FunctionTests(SimpleTestCase):

    def test_non_string_input(self):
        self.assertEqual(escape(123), '123')
