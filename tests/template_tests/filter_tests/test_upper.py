from django.template.defaultfilters import upper
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class UpperTests(SimpleTestCase):
    """
    The "upper" filter should preserve HTML safety, just like the "lower" filter.
    """

    @setup(
        {
            "upper01": (
                "{% autoescape off %}{{ a|upper }} {{ b|upper }}{% endautoescape %}"
            )
        }
    )
    def test_upper01(self):
        output = self.engine.render_to_string(
            "upper01", {"a": "a & b", "b": mark_safe("a &amp; b")}
        )
        self.assertEqual(output, "A & B A &AMP; B")

    @setup({"upper02": "{{ a|upper }} {{ b|upper }}"})
    def test_upper02(self):
        output = self.engine.render_to_string(
            "upper02", {"a": "a & b", "b": mark_safe("a &amp; b")}
        )
        self.assertEqual(output, "A &amp; B A &AMP; B")

    @setup({"upper03": "{{ html|upper }}"})
    def test_upper03(self):
        html = mark_safe("<p>Hello World!</p>")
        output = self.engine.render_to_string("upper03", {"html": html})
        self.assertEqual(output, "<P>HELLO WORLD!</P>")


class FunctionTests(SimpleTestCase):
    def test_upper(self):
        self.assertEqual(upper("Mixed case input"), "MIXED CASE INPUT")

    def test_unicode(self):
        # lowercase e umlaut
        self.assertEqual(upper("\xeb"), "\xcb")

    def test_non_string_input(self):
        self.assertEqual(upper(123), "123")
