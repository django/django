from django.template.defaultfilters import rjust
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class RjustTests(SimpleTestCase):
    @setup(
        {
            "rjust01": (
                '{% autoescape off %}.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.'
                "{% endautoescape %}"
            )
        }
    )
    def test_rjust01(self):
        output = self.engine.render_to_string(
            "rjust01", {"a": "a&b", "b": mark_safe("a&b")}
        )
        self.assertEqual(output, ".  a&b. .  a&b.")

    @setup({"rjust02": '.{{ a|rjust:"5" }}. .{{ b|rjust:"5" }}.'})
    def test_rjust02(self):
        output = self.engine.render_to_string(
            "rjust02", {"a": "a&b", "b": mark_safe("a&b")}
        )
        self.assertEqual(output, ".  a&amp;b. .  a&b.")


class FunctionTests(SimpleTestCase):
    def test_rjust(self):
        self.assertEqual(rjust("test", 10), "      test")

    def test_less_than_string_length(self):
        self.assertEqual(rjust("test", 3), "test")

    def test_non_string_input(self):
        self.assertEqual(rjust(123, 4), " 123")
