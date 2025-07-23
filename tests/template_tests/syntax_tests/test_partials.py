from unittest import mock

from django.template import NodeList, PartialTemplate, TemplateSyntaxError
from django.test import SimpleTestCase
from django.views.debug import ExceptionReporter

from ..utils import setup

partial_templates = {
    "partial-basic": (
        "{% partialdef test-partial %}TEST-PARTIAL-CONTENT{% endpartialdef %}"
    ),
    "partial-examples": """{% partialdef test-partial %}
TEST-PARTIAL-CONTENT
{% endpartialdef %}

{% block main %}
BEGINNING
{% partial test-partial %}
MIDDLE
{% partial test-partial %}
END
{% endblock main %}

{% partialdef inline-partial inline %}
INLINE-CONTENT
{% endpartialdef %}""",
    "partial_base.html": "{% block main %}{% endblock main %}",
    "partial_included.html": """INCLUDED TEMPLATE START
{% partialdef included-partial %}
THIS IS CONTENT FROM THE INCLUDED PARTIAL
{% endpartialdef %}

Now using the partial: {% partial included-partial %}
INCLUDED TEMPLATE END""",
}


class PartialTagTests(SimpleTestCase):
    @setup(
        {
            "partial01": (
                "{% partialdef testing-partial %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial01(self):
        output = self.engine.render_to_string("partial01")
        self.assertEqual(output, "HERE IS THE TEST CONTENT")

    @setup(
        {
            "partial02": (
                "{% partialdef testing-partial inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
            )
        }
    )
    def test_partial02(self):
        output = self.engine.render_to_string("partial02")
        self.assertEqual(output.strip(), "HERE IS THE TEST CONTENT")

    @setup(
        {
            "partial03": (
                "BEFORE\n"
                "{% partialdef testing-partial inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}\n"
                "AFTER"
            )
        }
    )
    def test_partial03(self):
        output = self.engine.render_to_string("partial03")
        self.assertEqual(output.strip(), "BEFORE\nHERE IS THE TEST CONTENT\nAFTER")

    @setup(
        {
            "partial04": (
                "{% partialdef testing-partial %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef testing-partial %}"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial04(self):
        output = self.engine.render_to_string("partial04")
        self.assertEqual(output, "HERE IS THE TEST CONTENT")

    @setup({"partial05": "{% partial undefined-partial %}"})
    def test_partial05(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "Partial 'undefined-partial' is not defined in the current template.",
        ):
            self.engine.render_to_string("partial05")

    @setup(
        {
            "partial06": (
                "BEFORE\n"
                "{% partialdef testing-partial inline %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef %}\n"
                "AFTER"
            )
        }
    )
    def test_partial06(self):
        output = self.engine.render_to_string("partial06")
        self.assertEqual(output.strip(), "BEFORE\n\nHERE IS THE TEST CONTENT\n\nAFTER")

    @setup(
        {
            "partial07": (
                "{% partialdef testing-partial %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef testing-partial %}\n"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial07(self):
        output = self.engine.render_to_string("partial07")
        self.assertEqual(output.strip(), "HERE IS THE TEST CONTENT")

    @setup(
        {
            "partial08": """TEMPLATE START
{% partial skeleton-partial %}
MIDDLE CONTENT
{% partialdef skeleton-partial %}
THIS IS THE SKELETON PARTIAL CONTENT
{% endpartialdef %}
TEMPLATE END"""
        }
    )
    def test_partial08(self):
        output = self.engine.render_to_string("partial08")
        self.assertIn("TEMPLATE START", output)
        self.assertIn("THIS IS THE SKELETON PARTIAL CONTENT", output)
        self.assertIn("MIDDLE CONTENT", output)
        self.assertIn("TEMPLATE END", output)

    @setup(
        {
            "partial09": """{% extends 'partial_base.html' %}
{% partialdef test-partial %}
Content inside partial
{% endpartialdef %}
{% block main %}
Main content with {% partial test-partial %}
{% endblock %}"""
        },
        partial_templates,
    )
    def test_partial09(self):
        output = self.engine.render_to_string("partial09")
        self.assertIn("Main content with", output)
        self.assertIn("Content inside partial", output)

    @setup(
        {
            "partial10": (
                "MAIN TEMPLATE START "
                "{% include 'partial_included.html' %} "
                "MAIN TEMPLATE END"
            )
        },
        partial_templates,
    )
    def test_partial_in_included_template(self):
        output = self.engine.render_to_string("partial10")
        self.assertIn("MAIN TEMPLATE START", output)
        self.assertIn("INCLUDED TEMPLATE START", output)
        self.assertIn("THIS IS CONTENT FROM THE INCLUDED PARTIAL", output)
        self.assertIn("INCLUDED TEMPLATE END", output)
        self.assertIn("MAIN TEMPLATE END", output)

    # Error cases
    @setup(
        {
            "partial-error01": (
                "{% partialdef testing-partial %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef invalid %}"
            )
        }
    )
    def test_partial_error01(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("partial-error01")

    @setup({"partial-error02": "{% partialdef %}"})
    def test_partial_error02(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "partialdef tag requires 2-3 arguments"
        ):
            self.engine.get_template("partial-error02")

    @setup({"partial-error03": "{% partialdef name inline extra %}"})
    def test_partial_error03(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "partialdef tag requires 2-3 arguments"
        ):
            self.engine.get_template("partial-error03")

    @setup({"partial-error04": "{% partial %}"})
    def test_partial_error04(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "'partial' tag requires a single argument"
        ):
            self.engine.get_template("partial-error04")

    @setup(
        {
            "partial-error05": (
                "{% partialdef test-partial inline=true %}"
                "Content"
                "{% endpartialdef %}"
            )
        }
    )
    def test_partial_error05(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "The 'inline' argument does not have any parameters"
        ):
            self.engine.get_template("partial-error05")

    @setup(
        {
            "partial-error06": (
                "{% partialdef testing-partial %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef invalid %}\n"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial_error06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string("partial-error06")

    @setup(
        {
            "partial-broken-unclosed": (
                "<div>Before partial</div>\n"
                "{% partialdef unclosed-partial %}\n"
                "<p>This partial has no closing tag</p>\n"
                "<div>After partial content</div>"
            )
        }
    )
    def test_broken_partial_unclosed_exception_info(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial-broken-unclosed")

        self.assertIn("endpartialdef", str(cm.exception))
        self.assertIn("Unclosed tag", str(cm.exception))

        reporter = ExceptionReporter(None, cm.exception.__class__, cm.exception, None)
        traceback_data = reporter.get_traceback_data()

        exception_value = str(traceback_data.get("exception_value", ""))
        self.assertIn("Unclosed tag", exception_value)

    def test_partial_template_get_exception_info(self):
        """Test that PartialTemplate.get_exception_info uses loader.get_template."""
        mock_origin = mock.Mock()
        mock_origin.template_name = "test_template.html"

        mock_loader = mock.Mock()
        mock_origin.loader = mock_loader

        mock_template = mock.Mock()
        mock_exception_info = {
            "line": 42,
            "name": "test_template.html",
            "message": "Test error message",
        }
        mock_template.get_exception_info.return_value = mock_exception_info
        mock_loader.get_template.return_value = mock_template

        proxy = PartialTemplate(NodeList(), mock_origin, "test-partial")

        test_exception = Exception("Test exception")
        mock_token = mock.Mock()
        mock_token.lineno = 10

        result = proxy.get_exception_info(test_exception, mock_token)

        mock_loader.get_template.assert_called_once_with("test_template.html")

        mock_template.get_exception_info.assert_called_once_with(
            test_exception, mock_token
        )

        self.assertEqual(result, mock_exception_info)
        self.assertEqual(result["line"], 42)
        self.assertEqual(result["name"], "test_template.html")
        self.assertEqual(result["message"], "Test error message")
