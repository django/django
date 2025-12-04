from django.test import SimpleTestCase
from django.utils.safestring import SafeString

from ..utils import setup


class RandomTests(SimpleTestCase):
    @setup({"random01": "{{ a|random }} {{ b|random }}"})
    def test_random01(self):
        output = self.engine.render_to_string(
            "random01",
            {"a": ["a&b", "a&b"], "b": [SafeString("a&b"), SafeString("a&b")]},
        )
        self.assertEqual(output, "a&amp;b a&b")

    @setup(
        {
            "random02": (
                "{% autoescape off %}{{ a|random }} {{ b|random }}{% endautoescape %}"
            )
        }
    )
    def test_random02(self):
        output = self.engine.render_to_string(
            "random02",
            {"a": ["a&b", "a&b"], "b": [SafeString("a&b"), SafeString("a&b")]},
        )
        self.assertEqual(output, "a&b a&b")

    @setup({"empty_list": "{{ list|random }}"})
    def test_empty_list(self):
        output = self.engine.render_to_string("empty_list", {"list": []})
        self.assertEqual(output, "")
