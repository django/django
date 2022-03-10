from django.template.defaultfilters import lower
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class LowerTests(SimpleTestCase):
    @setup(
        {
            "lower01": (
                "{% autoescape off %}{{ a|lower }} {{ b|lower }}{% endautoescape %}"
            )
        }
    )
    def test_lower01(self):
        output = self.engine.render_to_string(
            "lower01", {"a": "Apple & banana", "b": mark_safe("Apple &amp; banana")}
        )
        self.assertEqual(output, "apple & banana apple &amp; banana")

    @setup({"lower02": "{{ a|lower }} {{ b|lower }}"})
    def test_lower02(self):
        output = self.engine.render_to_string(
            "lower02", {"a": "Apple & banana", "b": mark_safe("Apple &amp; banana")}
        )
        self.assertEqual(output, "apple &amp; banana apple &amp; banana")


class FunctionTests(SimpleTestCase):
    def test_lower(self):
        self.assertEqual(lower("TEST"), "test")

    def test_unicode(self):
        # uppercase E umlaut
        self.assertEqual(lower("\xcb"), "\xeb")

    def test_non_string_input(self):
        self.assertEqual(lower(123), "123")
