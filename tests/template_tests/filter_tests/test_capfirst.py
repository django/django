from django.template.defaultfilters import capfirst
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class CapfirstTests(SimpleTestCase):
    @setup(
        {
            "capfirst01": (
                "{% autoescape off %}{{ a|capfirst }} {{ b|capfirst }}"
                "{% endautoescape %}"
            )
        }
    )
    def test_capfirst01(self):
        output = self.engine.render_to_string(
            "capfirst01", {"a": "fred>", "b": mark_safe("fred&gt;")}
        )
        self.assertEqual(output, "Fred> Fred&gt;")

    @setup({"capfirst02": "{{ a|capfirst }} {{ b|capfirst }}"})
    def test_capfirst02(self):
        output = self.engine.render_to_string(
            "capfirst02", {"a": "fred>", "b": mark_safe("fred&gt;")}
        )
        self.assertEqual(output, "Fred&gt; Fred&gt;")


class FunctionTests(SimpleTestCase):
    def test_capfirst(self):
        self.assertEqual(capfirst("hello world"), "Hello world")
