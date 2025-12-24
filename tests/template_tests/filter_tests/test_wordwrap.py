from django.template.defaultfilters import wordwrap
from django.test import SimpleTestCase
from django.utils.functional import lazystr
from django.utils.safestring import mark_safe

from ..utils import setup


class WordwrapTests(SimpleTestCase):
    @setup(
        {
            "wordwrap01": (
                '{% autoescape off %}{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}'
                "{% endautoescape %}"
            )
        }
    )
    def test_wordwrap01(self):
        output = self.engine.render_to_string(
            "wordwrap01", {"a": "a & b", "b": mark_safe("a & b")}
        )
        self.assertEqual(output, "a &\nb a &\nb")

    @setup({"wordwrap02": '{{ a|wordwrap:"3" }} {{ b|wordwrap:"3" }}'})
    def test_wordwrap02(self):
        output = self.engine.render_to_string(
            "wordwrap02", {"a": "a & b", "b": mark_safe("a & b")}
        )
        self.assertEqual(output, "a &amp;\nb a &\nb")


class FunctionTests(SimpleTestCase):
    def test_wrap(self):
        self.assertEqual(
            wordwrap(
                "this is a long paragraph of text that really needs to be wrapped I'm "
                "afraid",
                14,
            ),
            "this is a long\nparagraph of\ntext that\nreally needs\nto be wrapped\n"
            "I'm afraid",
        )

    def test_indent(self):
        self.assertEqual(
            wordwrap(
                "this is a short paragraph of text.\n  But this line should be "
                "indented",
                14,
            ),
            "this is a\nshort\nparagraph of\ntext.\n  But this\nline should be\n"
            "indented",
        )

    def test_indent2(self):
        self.assertEqual(
            wordwrap(
                "this is a short paragraph of text.\n  But this line should be "
                "indented",
                15,
            ),
            "this is a short\nparagraph of\ntext.\n  But this line\nshould be\n"
            "indented",
        )

    def test_non_string_input(self):
        self.assertEqual(wordwrap(123, 2), "123")

    def test_wrap_lazy_string(self):
        self.assertEqual(
            wordwrap(
                lazystr(
                    "this is a long paragraph of text that really needs to be wrapped "
                    "I'm afraid"
                ),
                14,
            ),
            "this is a long\nparagraph of\ntext that\nreally needs\nto be wrapped\n"
            "I'm afraid",
        )

    def test_wrap_long_text(self):
        long_text = (
            "this is a long paragraph of text that really needs"
            " to be wrapped I'm afraid " * 20_000
        )
        self.assertIn(
            "this is a\nlong\nparagraph\nof text\nthat\nreally\nneeds to\nbe wrapped\n"
            "I'm afraid",
            wordwrap(long_text, 10),
        )

    def test_wrap_preserve_newlines(self):
        cases = [
            (
                "this is a long paragraph of text that really needs to be wrapped\n\n"
                "that is followed by another paragraph separated by an empty line\n",
                "this is a long paragraph of\ntext that really needs to be\nwrapped\n\n"
                "that is followed by another\nparagraph separated by an\nempty line\n",
                30,
            ),
            ("\n\n\n", "\n\n\n", 5),
            ("\n\n\n\n\n\n", "\n\n\n\n\n\n", 5),
        ]
        for text, expected, width in cases:
            with self.subTest(text=text):
                self.assertEqual(wordwrap(text, width), expected)

    def test_wrap_preserve_whitespace(self):
        width = 5
        width_spaces = " " * width
        cases = [
            (
                f"first line\n{width_spaces}\nsecond line",
                f"first\nline\n{width_spaces}\nsecond\nline",
            ),
            (
                "first line\n \t\t\t \nsecond line",
                "first\nline\n \t\t\t \nsecond\nline",
            ),
            (
                f"first line\n{width_spaces}\nsecond line\n\nthird{width_spaces}\n",
                f"first\nline\n{width_spaces}\nsecond\nline\n\nthird\n",
            ),
            (
                f"first line\n{width_spaces}{width_spaces}\nsecond line",
                f"first\nline\n{width_spaces}{width_spaces}\nsecond\nline",
            ),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(wordwrap(text, width), expected)
