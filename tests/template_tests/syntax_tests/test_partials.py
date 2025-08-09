from django.template import (
    Context,
    TemplateDoesNotExist,
    TemplateSyntaxError,
    VariableDoesNotExist,
)
from django.template.base import Token, TokenType
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
    libraries = {"bad_tag": "template_tests.templatetags.bad_tag"}

    @setup(
        {
            "basic-partial-definition": (
                "{% partialdef testing-partial %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial_not_inline_used_once(self):
        output = self.engine.render_to_string("basic-partial-definition")
        self.assertEqual(output, "HERE IS THE TEST CONTENT")

    @setup(
        {
            "inline-partial-definition": (
                "{% partialdef testing-partial inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
            )
        }
    )
    def test_partial_inline_only(self):
        output = self.engine.render_to_string("inline-partial-definition")
        self.assertEqual(output.strip(), "HERE IS THE TEST CONTENT")

    @setup(
        {
            "inline-partial-with-context": (
                "BEFORE\n"
                "{% partialdef testing-partial inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}\n"
                "AFTER"
            )
        }
    )
    def test_partial_inline_only_with_before_and_after_content(self):
        output = self.engine.render_to_string("inline-partial-with-context")
        self.assertEqual(output.strip(), "BEFORE\nHERE IS THE TEST CONTENT\nAFTER")

    @setup(
        {
            "inline-partial-explicit-end": (
                "{% partialdef testing-partial inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef testing-partial %}\n"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial_inline_and_used_once(self):
        output = self.engine.render_to_string("inline-partial-explicit-end")
        self.assertEqual(output, "HERE IS THE TEST CONTENT\nHERE IS THE TEST CONTENT")

    @setup(
        {
            "inline-partial-with-usage": (
                "BEFORE\n"
                "{% partialdef content-snippet inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}\n"
                "AFTER\n"
                "{% partial content-snippet %}"
            )
        }
    )
    def test_partial_inline_and_used_once_with_before_and_after_content(self):
        output = self.engine.render_to_string("inline-partial-with-usage")
        self.assertEqual(
            output.strip(),
            "BEFORE\nHERE IS THE TEST CONTENT\nAFTER\nHERE IS THE TEST CONTENT",
        )

    @setup(
        {
            "partial-with-newlines": (
                "{% partialdef testing-partial %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef testing-partial %}\n"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial_rendering_with_optional_endname(self):
        output = self.engine.render_to_string("partial-with-newlines")
        self.assertEqual(output.strip(), "HERE IS THE TEST CONTENT")

    @setup(
        {
            "partial-used-before-definition": """TEMPLATE START
{% partial skeleton-partial %}
MIDDLE CONTENT
{% partialdef skeleton-partial %}
THIS IS THE SKELETON PARTIAL CONTENT
{% endpartialdef %}
TEMPLATE END"""
        }
    )
    def test_partial_used_before_definition(self):
        output = self.engine.render_to_string("partial-used-before-definition")
        self.assertIn("TEMPLATE START", output)
        self.assertIn("THIS IS THE SKELETON PARTIAL CONTENT", output)
        self.assertIn("MIDDLE CONTENT", output)
        self.assertIn("TEMPLATE END", output)

    @setup(
        {
            "partial-with-extends": """{% extends 'partial_base.html' %}
{% partialdef test-partial %}
Content inside partial
{% endpartialdef %}
{% block main %}
Main content with {% partial test-partial %}
{% endblock %}"""
        },
        partial_templates,
    )
    def test_partial_defined_outside_main_block(self):
        output = self.engine.render_to_string("partial-with-extends")
        self.assertIn("Main content with", output)
        self.assertIn("Content inside partial", output)

    @setup(
        {
            "partial-with-include": (
                "MAIN TEMPLATE START "
                "{% include 'partial_included.html' %} "
                "MAIN TEMPLATE END"
            )
        },
        partial_templates,
    )
    def test_partial_in_included_template(self):
        output = self.engine.render_to_string("partial-with-include")
        self.assertIn("MAIN TEMPLATE START", output)
        self.assertIn("INCLUDED TEMPLATE START", output)
        self.assertIn("THIS IS CONTENT FROM THE INCLUDED PARTIAL", output)
        self.assertIn("INCLUDED TEMPLATE END", output)
        self.assertIn("MAIN TEMPLATE END", output)

    # Error cases
    @setup(
        {
            "undefined_name": "{% partial undefined-partial %}",
            "partial_missing_name": "{% partial %}",
            "partialdef_missing_name": "{% partialdef %}TEST{% endpartialdef %}",
            "partialdef_extra_params": (
                "{% partialdef name inline extra %}TEST{% endpartialdef %}"
            ),
            "partialdef_missing_close_tag": "{% partialdef %}",
            "partial-error01": (
                "{% partialdef partial-name %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef invalid %}"
            ),
            "partial-error05": (
                "{% partialdef test-partial inline=true %}"
                "Content"
                "{% endpartialdef %}"
            ),
            "partial-error06": (
                "{% partialdef test-partial inline invalid %}"
                "Content"
                "{% endpartialdef %}"
            ),
            "partial-error07": (
                "{% partialdef partial-name %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef invalid %}\n"
                "{% partial partial-name %}"
            ),
        }
    )
    def test_basic_parse_errors(self):
        for template_name, error_msg in (
            (
                "undefined_name",
                "Partial 'undefined-partial' is not defined in the current template.",
            ),
            ("partial_missing_name", "'partial' tag requires a single argument"),
            ("partialdef_missing_name", "partialdef tag requires 2-3 arguments"),
            ("partialdef_missing_close_tag", "partialdef tag requires 2-3 arguments"),
            (
                "partial-error01",
                "expected 'endpartialdef' or 'endpartialdef partial-name'.",
            ),
            ("partial-error05", "The 'inline' argument does not have any parameters"),
            ("partial-error06", "partialdef tag requires 2-3 arguments"),
            (
                "partial-error07",
                "expected 'endpartialdef' or 'endpartialdef partial-name'.",
            ),
        ):
            with (
                self.subTest(template_name=template_name),
                self.assertRaisesMessage(TemplateSyntaxError, error_msg),
            ):
                self.engine.render_to_string(template_name)

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

    @setup(
        {
            "partial-with-variable-error": """<h1>Title</h1>
{% partialdef test-partial %}
<p>{{ nonexistent|default:alsonotthere }}</p>
{% endpartialdef %}
<h2>Sub Title</h2>
{% partial test-partial %}
""",
        }
    )
    def test_partial_runtime_exception_has_debug_info(self):
        template = self.engine.get_template("partial-with-variable-error")
        context = Context({})

        if hasattr(self.engine, "string_if_invalid") and self.engine.string_if_invalid:
            output = template.render(context)
            # The variable should be replaced with INVALID
            self.assertIn("INVALID", output)
        else:
            with self.assertRaises(VariableDoesNotExist) as cm:
                template.render(context)

            if self.engine.debug:
                exc_info = cm.exception.template_debug

                self.assertEqual(
                    exc_info["during"], "{{ nonexistent|default:alsonotthere }}"
                )
                self.assertEqual(exc_info["line"], 3)
                self.assertEqual(exc_info["name"], "partial-with-variable-error")
                self.assertIn("Failed lookup", exc_info["message"])

    @setup(
        {
            "partial-exception-info-test": """<h1>Title</h1>
{% partialdef test-partial %}
<p>Content</p>
{% endpartialdef %}
""",
        }
    )
    def test_partial_template_get_exception_info_delegation(self):
        if self.engine.debug:
            template = self.engine.get_template("partial-exception-info-test")

            partial_template = template.extra_data["template-partials"]["test-partial"]

            test_exc = Exception("Test exception")
            token = Token(
                token_type=TokenType.VAR,
                contents="test",
                position=(0, 4),
            )

            exc_info = partial_template.get_exception_info(test_exc, token)
            self.assertIn("message", exc_info)
            self.assertIn("line", exc_info)
            self.assertIn("name", exc_info)
            self.assertEqual(exc_info["name"], "partial-exception-info-test")
            self.assertEqual(exc_info["message"], "Test exception")

    @setup(
        {
            "partial-with-undefined-reference": """<h1>Header</h1>
{% partial undefined-partial %}
<p>After undefined partial</p>
""",
        }
    )
    def test_undefined_partial_exception_info(self):
        template = self.engine.get_template("partial-with-undefined-reference")
        with self.assertRaises(TemplateSyntaxError) as cm:
            template.render(Context())

        self.assertIn("undefined-partial", str(cm.exception))
        self.assertIn("is not defined", str(cm.exception))

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertEqual(exc_debug["during"], "{% partial undefined-partial %}")
            self.assertEqual(exc_debug["line"], 2)
            self.assertEqual(exc_debug["name"], "partial-with-undefined-reference")
            self.assertIn("undefined-partial", exc_debug["message"])

    @setup(
        {
            "existing_template": """<h1>Header</h1>
<p>This template has no partials defined</p>
""",
        }
    )
    def test_undefined_partial_exception_info_template_does_not_exist(self):
        with self.assertRaises(TemplateDoesNotExist) as cm:
            self.engine.get_template("existing_template#undefined-partial")

        self.assertIn("undefined-partial", str(cm.exception))

    @setup(
        {
            "partial-with-syntax-error": """<h1>Title</h1>
{% partialdef syntax-error-partial %}
    {% if user %}
        <p>User: {{ user.name }}</p>
    {% endif
    <p>Missing closing tag above</p>
{% endpartialdef %}
{% partial syntax-error-partial %}
""",
        }
    )
    def test_partial_with_syntax_error_exception_info(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial-with-syntax-error")

        self.assertIn("endif", str(cm.exception).lower())

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertIn("endpartialdef", exc_debug["during"])
            self.assertEqual(exc_debug["name"], "partial-with-syntax-error")
            self.assertIn("endif", exc_debug["message"].lower())

    @setup(
        {
            "partial-with-runtime-error": """<h1>Title</h1>
{% load bad_tag %}
{% partialdef runtime-error-partial %}
    <p>This will raise an error:</p>
    {% badsimpletag %}
{% endpartialdef %}
{% partial runtime-error-partial %}
""",
        }
    )
    def test_partial_runtime_error_exception_info(self):
        template = self.engine.get_template("partial-with-runtime-error")
        context = Context()

        with self.assertRaises(RuntimeError) as cm:
            template.render(context)

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertIn("badsimpletag", exc_debug["during"])
            self.assertEqual(exc_debug["line"], 5)  # Line 5 is where badsimpletag is
            self.assertEqual(exc_debug["name"], "partial-with-runtime-error")
            self.assertIn("bad simpletag", exc_debug["message"])

    @setup(
        {
            "nested-partial-with-undefined-var": """<h1>Title</h1>
{% partialdef outer-partial %}
    <div class="outer">
        {% partialdef inner-partial %}
            <p>{{ undefined_var }}</p>
        {% endpartialdef %}
        {% partial inner-partial %}
    </div>
{% endpartialdef %}
{% partial outer-partial %}
""",
        }
    )
    def test_nested_partial_error_exception_info(self):
        template = self.engine.get_template("nested-partial-with-undefined-var")
        context = Context()
        output = template.render(context)

        # When string_if_invalid is set, it will show INVALID
        # When not set, undefined variables just render as empty string
        if hasattr(self.engine, "string_if_invalid") and self.engine.string_if_invalid:
            self.assertIn("INVALID", output)
        else:
            self.assertIn("<p>", output)
            self.assertIn("</p>", output)

    @setup(
        {
            "parent.html": """<!DOCTYPE html>
<html>
<head>{% block title %}Default Title{% endblock %}</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
""",
            "child.html": """{% extends "parent.html" %}
{% block content %}
    {% partialdef content-partial %}
        <p>{{ missing_variable|undefined_filter }}</p>
    {% endpartialdef %}
    {% partial content-partial %}
{% endblock %}
""",
        }
    )
    def test_partial_in_extended_template_error(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("child.html")

        self.assertIn("undefined_filter", str(cm.exception))

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertIn("undefined_filter", exc_debug["during"])
            self.assertEqual(exc_debug["name"], "child.html")
            self.assertIn("undefined_filter", exc_debug["message"])

    @setup(
        {
            "partial-broken-nesting": (
                "<div>Before partial</div>\n"
                "{% partialdef outer %}\n"
                "{% partialdef inner %}...{% endpartialdef outer %}\n"
                "{% endpartialdef inner %}\n"
                "<div>After partial content</div>"
            )
        }
    )
    def test_broken_partial_nesting(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial-broken-nesting")

        self.assertIn("endpartialdef", str(cm.exception))
        self.assertIn("Invalid block tag", str(cm.exception))
        self.assertIn("'endpartialdef inner'", str(cm.exception))

        reporter = ExceptionReporter(None, cm.exception.__class__, cm.exception, None)
        traceback_data = reporter.get_traceback_data()

        exception_value = str(traceback_data.get("exception_value", ""))
        self.assertIn("Invalid block tag", exception_value)
        self.assertIn("'endpartialdef inner'", str(cm.exception))

    @setup(
        {
            "partial-broken-nesting-mixed": (
                "<div>Before partial</div>\n"
                "{% partialdef outer %}\n"
                "{% partialdef inner %}...{% endpartialdef %}\n"
                "{% endpartialdef inner %}\n"
                "<div>After partial content</div>"
            )
        }
    )
    def test_broken_partial_nesting_mixed(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial-broken-nesting-mixed")

        self.assertIn("endpartialdef", str(cm.exception))
        self.assertIn("Invalid block tag", str(cm.exception))
        self.assertIn("'endpartialdef outer'", str(cm.exception))

        reporter = ExceptionReporter(None, cm.exception.__class__, cm.exception, None)
        traceback_data = reporter.get_traceback_data()

        exception_value = str(traceback_data.get("exception_value", ""))
        self.assertIn("Invalid block tag", exception_value)
        self.assertIn("'endpartialdef outer'", str(cm.exception))
