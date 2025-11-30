from django.template.defaultfilters import center
from django.test import SimpleTestCase
from django.utils.safestring import SafeString

from ..utils import setup


class CenterTests(SimpleTestCase):
    @setup(
        {
            "center01": (
                '{% autoescape off %}.{{ a|center:"5" }}. .{{ b|center:"5" }}.'
                "{% endautoescape %}"
            )
        }
    )
    def test_center01(self):
        output = self.engine.render_to_string(
            "center01", {"a": "a&b", "b": SafeString("a&b")}
        )
        self.assertEqual(output, ". a&b . . a&b .")

    @setup({"center02": '.{{ a|center:"5" }}. .{{ b|center:"5" }}.'})
    def test_center02(self):
        output = self.engine.render_to_string(
            "center02", {"a": "a&b", "b": SafeString("a&b")}
        )
        self.assertEqual(output, ". a&amp;b . . a&b .")


class FunctionTests(SimpleTestCase):
    def test_center(self):
        self.assertEqual(center("test", 6), " test ")

    def test_non_string_input(self):
        self.assertEqual(center(123, 5), " 123 ")

    def test_odd_input(self):
        self.assertEqual(center("odd", 6), " odd  ")

    def test_even_input(self):
        self.assertEqual(center("even", 7), " even  ")

    def test_widths(self):
        value = "something"
        for i in range(-1, len(value) + 1):
            with self.subTest(i=i):
                self.assertEqual(center(value, i), value)
