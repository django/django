from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class VerbatimTagTests(SimpleTestCase):
    @setup({"verbatim-tag01": "{% verbatim %}{{bare   }}{% endverbatim %}"})
    def test_verbatim_tag01(self):
        output = self.engine.render_to_string("verbatim-tag01")
        self.assertEqual(output, "{{bare   }}")

    @setup({"verbatim-tag02": "{% verbatim %}{% endif %}{% endverbatim %}"})
    def test_verbatim_tag02(self):
        output = self.engine.render_to_string("verbatim-tag02")
        self.assertEqual(output, "{% endif %}")

    @setup(
        {"verbatim-tag03": "{% verbatim %}It's the {% verbatim %} tag{% endverbatim %}"}
    )
    def test_verbatim_tag03(self):
        output = self.engine.render_to_string("verbatim-tag03")
        self.assertEqual(output, "It's the {% verbatim %} tag")

    @setup(
        {
            "verbatim-tag04": (
                "{% verbatim %}{% verbatim %}{% endverbatim %}{% endverbatim %}"
            )
        }
    )
    def test_verbatim_tag04(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("verbatim-tag04")

    @setup(
        {
            "verbatim-tag05": (
                "{% verbatim %}{% endverbatim %}{% verbatim %}{% endverbatim %}"
            )
        }
    )
    def test_verbatim_tag05(self):
        output = self.engine.render_to_string("verbatim-tag05")
        self.assertEqual(output, "")

    @setup(
        {
            "verbatim-tag06": "{% verbatim special %}"
            "Don't {% endverbatim %} just yet{% endverbatim special %}"
        }
    )
    def test_verbatim_tag06(self):
        output = self.engine.render_to_string("verbatim-tag06")
        self.assertEqual(output, "Don't {% endverbatim %} just yet")

    @setup(
        {
            "single_braces": (
                "{% verbatim %}{{% endverbatim %}"
                "text"
                "{% verbatim %}}{% endverbatim %}"
            ),
            "double_braces": (
                "{% verbatim %}{{{% endverbatim %}"
                "text"
                "{% verbatim %}}}{% endverbatim %}"
            ),
            "double_braces_with_spaces": (
                "{% verbatim %}{{ {% endverbatim %}"
                "text"
                "{% verbatim %} }}{% endverbatim %}"
            ),
        }
    )
    def test_multiple_verbatim_tags_on_same_line(self):
        tests = {
            "single_braces": "{text}",
            "double_braces": "{{text}}",
            "double_braces_with_spaces": "{{ text }}",
        }
        for template_name, expected in tests.items():
            with self.subTest(template_name=template_name):
                output = self.engine.render_to_string(template_name)
                self.assertEqual(output, expected)

    @setup(
        {
            "named_verbatim": (
                "{% verbatim example %}\n"
                "{%\n"
                "{% endverbatim %}\n"
                "{% endverbatim example %}"
            ),
        }
    )
    def test_literal_multiline_opener_in_named_verbatim(self):
        output = self.engine.render_to_string("named_verbatim")
        self.assertEqual(
            output,
            "\n{%\n{% endverbatim %}\n",
        )

    @setup({"verbatim": "{% verbatim %}content{%\n" "endverbatim\n" "%}"})
    def test_multiline_raw_block_closing_tags(self):
        output = self.engine.render_to_string("verbatim")
        self.assertEqual(output, "content")

    @setup(
        {
            "verbatim": (
                "{% verbatim %}\n"
                "{% if user %}Hello, {{ user }}{% endif %}\n"
                "{% endverbatim %}"
            ),
        }
    )
    def test_template_syntax_in_raw_blocks(self):
        output = self.engine.render_to_string("verbatim")
        self.assertEqual(output, "\n{% if user %}Hello, {{ user }}{% endif %}\n")

    @setup({"verbatim": "{% verbatim %}\n{%\n{% endverbatim %}"})
    def test_literal_multiline_block_opener_in_raw_blocks(self):
        output = self.engine.render_to_string("verbatim")
        self.assertEqual(output, "\n{%\n")

    @setup(
        {
            "verbatim": (
                "{% verbatim example %}"
                "content"
                "{%\n"
                "    endverbatim\n"
                "    example\n"
                "%}"
            ),
        }
    )
    def test_multiline_named_closing_tag(self):
        output = self.engine.render_to_string("verbatim")
        self.assertEqual(output, "content")
