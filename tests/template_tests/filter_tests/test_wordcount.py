from django.template.defaultfilters import wordcount
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class WordcountTests(SimpleTestCase):
    @setup(
        {
            "wordcount01": (
                "{% autoescape off %}{{ a|wordcount }} {{ b|wordcount }}"
                "{% endautoescape %}"
            )
        }
    )
    def test_wordcount01(self):
        output = self.engine.render_to_string(
            "wordcount01", {"a": "a & b", "b": mark_safe("a &amp; b")}
        )
        self.assertEqual(output, "3 3")

    @setup({"wordcount02": "{{ a|wordcount }} {{ b|wordcount }}"})
    def test_wordcount02(self):
        output = self.engine.render_to_string(
            "wordcount02", {"a": "a & b", "b": mark_safe("a &amp; b")}
        )
        self.assertEqual(output, "3 3")


class FunctionTests(SimpleTestCase):
    def test_empty_string(self):
        self.assertEqual(wordcount(""), 0)

    def test_count_one(self):
        self.assertEqual(wordcount("oneword"), 1)

    def test_count_multiple(self):
        self.assertEqual(wordcount("lots of words"), 3)

    def test_non_string_input(self):
        self.assertEqual(wordcount(123), 1)
