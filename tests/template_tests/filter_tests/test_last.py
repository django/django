from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class LastTests(SimpleTestCase):

    @setup({'last01': '{{ a|last }} {{ b|last }}'})
    def test_last01(self):
        output = self.engine.render_to_string('last01', {"a": ["x", "a&b"], "b": ["x", mark_safe("a&b")]})
        self.assertEqual(output, "a&amp;b a&b")

    @setup({'last02': '{% autoescape off %}{{ a|last }} {{ b|last }}{% endautoescape %}'})
    def test_last02(self):
        output = self.engine.render_to_string('last02', {"a": ["x", "a&b"], "b": ["x", mark_safe("a&b")]})
        self.assertEqual(output, "a&b a&b")
