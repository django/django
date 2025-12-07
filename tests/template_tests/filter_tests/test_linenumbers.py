from django.template.defaultfilters import linenumbers
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class LinenumbersTests(SimpleTestCase):
    """
    The contents of "linenumbers" is escaped according to the current
    autoescape setting.
    """

    @setup({"linenumbers01": "{{ a|linenumbers }} {{ b|linenumbers }}"})
    def test_linenumbers01(self):
        output = self.engine.render_to_string(
            "linenumbers01",
            {"a": "one\n<two>\nthree", "b": mark_safe("one\n&lt;two&gt;\nthree")},
        )
        self.assertEqual(
            output, "1. one\n2. &lt;two&gt;\n3. three 1. one\n2. &lt;two&gt;\n3. three"
        )

    @setup(
        {
            "linenumbers02": (
                "{% autoescape off %}{{ a|linenumbers }} {{ b|linenumbers }}"
                "{% endautoescape %}"
            )
        }
    )
    def test_linenumbers02(self):
        output = self.engine.render_to_string(
            "linenumbers02",
            {"a": "one\n<two>\nthree", "b": mark_safe("one\n&lt;two&gt;\nthree")},
        )
        self.assertEqual(
            output, "1. one\n2. <two>\n3. three 1. one\n2. &lt;two&gt;\n3. three"
        )


class FunctionTests(SimpleTestCase):
    def test_linenumbers(self):
        self.assertEqual(linenumbers("line 1\nline 2"), "1. line 1\n2. line 2")

    def test_linenumbers2(self):
        self.assertEqual(
            linenumbers("\n".join(["x"] * 10)),
            "01. x\n02. x\n03. x\n04. x\n05. x\n06. x\n07. x\n08. x\n09. x\n10. x",
        )

    def test_non_string_input(self):
        self.assertEqual(linenumbers(123), "1. 123")

    def test_autoescape(self):
        self.assertEqual(
            linenumbers("foo\n<a>bar</a>\nbuz"),
            "1. foo\n2. &lt;a&gt;bar&lt;/a&gt;\n3. buz",
        )

    def test_autoescape_off(self):
        self.assertEqual(
            linenumbers("foo\n<a>bar</a>\nbuz", autoescape=False),
            "1. foo\n2. <a>bar</a>\n3. buz",
        )
