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
    "partial_base.html": (
        "<main>{% block main %}Default main content.{% endblock main %}</main>"
    ),
    "partial_included.html": (
        "INCLUDED TEMPLATE START\n"
        "{% partialdef included-partial %}\n"
        "THIS IS CONTENT FROM THE INCLUDED PARTIAL\n"
        "{% endpartialdef %}\n\n"
        "Now using the partial: {% partial included-partial %}\n"
        "INCLUDED TEMPLATE END\n"
    ),
}

valid_partialdef_names = (
    "dot.in.name",
    "'space in name'",
    "exclamation!",
    "@at",
    "slash/something",
    "inline",
    "inline-inline",
    "INLINE" "with+plus",
    "with&amp",
    "with%percent",
    "with,comma",
    "with:colon",
    "with;semicolon",
    "[brackets]",
    "(parens)",
    "{curly}",
)


def gen_partial_template(name, *args, **kwargs):
    if args or kwargs:
        extra = " ".join((args, *("{k}={v}" for k, v in kwargs.items()))) + " "
    else:
        extra = ""
    return (
        f"{{% partialdef {name} {extra}%}}TEST with {name}!{{% endpartialdef %}}"
        f"{{% partial {name} %}}"
    )


class PartialTagTests(SimpleTestCase):
    libraries = {"bad_tag": "template_tests.templatetags.bad_tag"}

    @setup({name: gen_partial_template(name) for name in valid_partialdef_names})
    def test_valid_partialdef_names(self):
        for template_name in valid_partialdef_names:
            with self.subTest(template_name=template_name):
                output = self.engine.render_to_string(template_name)
                self.assertEqual(output, f"TEST with {template_name}!")

    @setup(
        {
            "basic": (
                "{% partialdef testing-name %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
                "{% partial testing-name %}"
            ),
            "basic_inline": (
                "{% partialdef testing-name inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
            ),
            "inline_inline": (
                "{% partialdef inline inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}"
            ),
            "with_newlines": (
                "{% partialdef testing-name %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef testing-name %}\n"
                "{% partial testing-name %}"
            ),
        }
    )
    def test_basic_usage(self):
        for template_name in (
            "basic",
            "basic_inline",
            "inline_inline",
            "with_newlines",
        ):
            with self.subTest(template_name=template_name):
                output = self.engine.render_to_string(template_name)
                self.assertEqual(output.strip(), "HERE IS THE TEST CONTENT")

    @setup(
        {
            "inline_partial_with_context": (
                "BEFORE\n"
                "{% partialdef testing-name inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}\n"
                "AFTER"
            )
        }
    )
    def test_partial_inline_only_with_before_and_after_content(self):
        output = self.engine.render_to_string("inline_partial_with_context")
        self.assertEqual(output.strip(), "BEFORE\nHERE IS THE TEST CONTENT\nAFTER")

    @setup(
        {
            "inline_partial_explicit_end": (
                "{% partialdef testing-name inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef testing-name %}\n"
                "{% partial testing-name %}"
            )
        }
    )
    def test_partial_inline_and_used_once(self):
        output = self.engine.render_to_string("inline_partial_explicit_end")
        self.assertEqual(output, "HERE IS THE TEST CONTENT\nHERE IS THE TEST CONTENT")

    @setup(
        {
            "inline_partial_with_usage": (
                "BEFORE\n"
                "{% partialdef content_snippet inline %}"
                "HERE IS THE TEST CONTENT"
                "{% endpartialdef %}\n"
                "AFTER\n"
                "{% partial content_snippet %}"
            )
        }
    )
    def test_partial_inline_and_used_once_with_before_and_after_content(self):
        output = self.engine.render_to_string("inline_partial_with_usage")
        self.assertEqual(
            output.strip(),
            "BEFORE\nHERE IS THE TEST CONTENT\nAFTER\nHERE IS THE TEST CONTENT",
        )

    @setup(
        {
            "partial_used_before_definition": (
                "TEMPLATE START\n"
                "{% partial testing-name %}\n"
                "MIDDLE CONTENT\n"
                "{% partialdef testing-name %}\n"
                "THIS IS THE PARTIAL CONTENT\n"
                "{% endpartialdef %}\n"
                "TEMPLATE END"
            ),
        }
    )
    def test_partial_used_before_definition(self):
        output = self.engine.render_to_string("partial_used_before_definition")
        expected = (
            "TEMPLATE START\n\nTHIS IS THE PARTIAL CONTENT\n\n"
            "MIDDLE CONTENT\n\nTEMPLATE END"
        )
        self.assertEqual(output, expected)

    @setup(
        {
            "partial_with_extends": (
                "{% extends 'partial_base.html' %}"
                "{% partialdef testing-name %}Inside Content{% endpartialdef %}"
                "{% block main %}"
                "Main content with {% partial testing-name %}"
                "{% endblock %}"
            ),
        },
        partial_templates,
    )
    def test_partial_defined_outside_main_block(self):
        output = self.engine.render_to_string("partial_with_extends")
        self.assertIn("<main>Main content with Inside Content</main>", output)

    @setup(
        {
            "partial_with_extends_and_block_super": (
                "{% extends 'partial_base.html' %}"
                "{% partialdef testing-name %}Inside Content{% endpartialdef %}"
                "{% block main %}{{ block.super }} "
                "Main content with {% partial testing-name %}"
                "{% endblock %}"
            ),
        },
        partial_templates,
    )
    def test_partial_used_with_block_super(self):
        output = self.engine.render_to_string("partial_with_extends_and_block_super")
        self.assertIn(
            "<main>Default main content. Main content with Inside Content</main>",
            output,
        )

    @setup(
        {
            "partial_with_include": (
                "MAIN TEMPLATE START\n"
                "{% include 'partial_included.html' %}\n"
                "MAIN TEMPLATE END"
            )
        },
        partial_templates,
    )
    def test_partial_in_included_template(self):
        output = self.engine.render_to_string("partial_with_include")
        expected = (
            "MAIN TEMPLATE START\nINCLUDED TEMPLATE START\n\n\n"
            "Now using the partial: \n"
            "THIS IS CONTENT FROM THE INCLUDED PARTIAL\n\n"
            "INCLUDED TEMPLATE END\n\nMAIN TEMPLATE END"
        )
        self.assertEqual(output, expected)

    @setup(
        {
            "partial_as_include_in_other_template": (
                "MAIN TEMPLATE START\n"
                "{% include 'partial_included.html#included-partial' %}\n"
                "MAIN TEMPLATE END"
            )
        },
        partial_templates,
    )
    def test_partial_as_include_in_template(self):
        output = self.engine.render_to_string("partial_as_include_in_other_template")
        expected = (
            "MAIN TEMPLATE START\n\n"
            "THIS IS CONTENT FROM THE INCLUDED PARTIAL\n\n"
            "MAIN TEMPLATE END"
        )
        self.assertEqual(output, expected)

    @setup(
        {
            "nested_simple": (
                "{% extends 'base.html' %}"
                "{% block content %}"
                "This is my main page."
                "{% partialdef outer inline %}"
                "    It hosts a couple of partials.\n"
                "    {% partialdef inner inline %}"
                "        And an inner one."
                "    {% endpartialdef inner %}"
                "{% endpartialdef outer %}"
                "{% endblock content %}"
            ),
            "use_outer": "{% include 'nested_simple#outer' %}",
            "use_inner": "{% include 'nested_simple#inner' %}",
        }
    )
    def test_nested_partials(self):
        with self.subTest(template_name="use_outer"):
            output = self.engine.render_to_string("use_outer")
            self.assertEqual(
                [line.strip() for line in output.split("\n")],
                ["It hosts a couple of partials.", "And an inner one."],
            )
        with self.subTest(template_name="use_inner"):
            output = self.engine.render_to_string("use_inner")
            self.assertEqual(output.strip(), "And an inner one.")

    @setup(
        {
            "partial_undefined_name": "{% partial undefined %}",
            "partial_missing_name": "{% partial %}",
            "partial_closing_tag": (
                "{% partialdef testing-name %}TEST{% endpartialdef %}"
                "{% partial testing-name %}{% endpartial %}"
            ),
            "partialdef_missing_name": "{% partialdef %}{% endpartialdef %}",
            "partialdef_missing_close_tag": "{% partialdef name %}TEST",
            "partialdef_opening_closing_name_mismatch": (
                "{% partialdef testing-name %}TEST{% endpartialdef invalid %}"
            ),
            "partialdef_invalid_name": gen_partial_template("with\nnewline"),
            "partialdef_extra_params": (
                "{% partialdef testing-name inline extra %}TEST{% endpartialdef %}"
            ),
            "partialdef_duplicated_names": (
                "{% partialdef testing-name %}TEST{% endpartialdef %}"
                "{% partialdef testing-name %}TEST{% endpartialdef %}"
                "{% partial testing-name %}"
            ),
            "partialdef_duplicated_nested_names": (
                "{% partialdef testing-name %}"
                "TEST"
                "{% partialdef testing-name %}TEST{% endpartialdef %}"
                "{% endpartialdef %}"
                "{% partial testing-name %}"
            ),
        },
    )
    def test_basic_parse_errors(self):
        for template_name, error_msg in (
            (
                "partial_undefined_name",
                "Partial 'undefined' is not defined in the current template.",
            ),
            ("partial_missing_name", "'partial' tag requires a single argument"),
            ("partial_closing_tag", "Invalid block tag on line 1: 'endpartial'"),
            ("partialdef_missing_name", "'partialdef' tag requires a name"),
            ("partialdef_missing_close_tag", "Unclosed tag on line 1: 'partialdef'"),
            (
                "partialdef_opening_closing_name_mismatch",
                "expected 'endpartialdef' or 'endpartialdef testing-name'.",
            ),
            ("partialdef_invalid_name", "Invalid block tag on line 3: 'endpartialdef'"),
            ("partialdef_extra_params", "'partialdef' tag takes at most 2 arguments"),
            (
                "partialdef_duplicated_names",
                "Partial 'testing-name' is already defined in the "
                "'partialdef_duplicated_names' template.",
            ),
            (
                "partialdef_duplicated_nested_names",
                "Partial 'testing-name' is already defined in the "
                "'partialdef_duplicated_nested_names' template.",
            ),
        ):
            with (
                self.subTest(template_name=template_name),
                self.assertRaisesMessage(TemplateSyntaxError, error_msg),
            ):
                self.engine.render_to_string(template_name)

    @setup(
        {
            "with_params": (
                "{% partialdef testing-name inline=true %}TEST{% endpartialdef %}"
            ),
            "uppercase": "{% partialdef testing-name INLINE %}TEST{% endpartialdef %}",
        }
    )
    def test_partialdef_invalid_inline(self):
        error_msg = "The 'inline' argument does not have any parameters"
        for template_name in ("with_params", "uppercase"):
            with (
                self.subTest(template_name=template_name),
                self.assertRaisesMessage(TemplateSyntaxError, error_msg),
            ):
                self.engine.render_to_string(template_name)

    @setup(
        {
            "partial_broken_unclosed": (
                "<div>Before partial</div>"
                "{% partialdef unclosed_partial %}"
                "<p>This partial has no closing tag</p>"
                "<div>After partial content</div>"
            )
        }
    )
    def test_broken_partial_unclosed_exception_info(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial_broken_unclosed")

        self.assertIn("endpartialdef", str(cm.exception))
        self.assertIn("Unclosed tag", str(cm.exception))

        reporter = ExceptionReporter(None, cm.exception.__class__, cm.exception, None)
        traceback_data = reporter.get_traceback_data()

        exception_value = str(traceback_data.get("exception_value", ""))
        self.assertIn("Unclosed tag", exception_value)

    @setup(
        {
            "partial_with_variable_error": (
                "<h1>Title</h1>\n"
                "{% partialdef testing-name %}\n"
                "<p>{{ nonexistent|default:alsonotthere }}</p>\n"
                "{% endpartialdef %}\n"
                "<h2>Sub Title</h2>\n"
                "{% partial testing-name %}\n"
            ),
        }
    )
    def test_partial_runtime_exception_has_debug_info(self):
        template = self.engine.get_template("partial_with_variable_error")
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
                self.assertEqual(exc_info["name"], "partial_with_variable_error")
                self.assertIn("Failed lookup", exc_info["message"])

    @setup(
        {
            "partial_exception_info_test": (
                "<h1>Title</h1>\n"
                "{% partialdef testing-name %}\n"
                "<p>Content</p>\n"
                "{% endpartialdef %}\n"
            ),
        }
    )
    def test_partial_template_get_exception_info_delegation(self):
        if self.engine.debug:
            template = self.engine.get_template("partial_exception_info_test")

            partial_template = template.extra_data["partials"]["testing-name"]

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
            self.assertEqual(exc_info["name"], "partial_exception_info_test")
            self.assertEqual(exc_info["message"], "Test exception")

    @setup(
        {
            "partial_with_undefined_reference": (
                "<h1>Header</h1>\n"
                "{% partial undefined %}\n"
                "<p>After undefined partial</p>\n"
            ),
        }
    )
    def test_undefined_partial_exception_info(self):
        template = self.engine.get_template("partial_with_undefined_reference")
        with self.assertRaises(TemplateSyntaxError) as cm:
            template.render(Context())

        self.assertIn("undefined", str(cm.exception))
        self.assertIn("is not defined", str(cm.exception))

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertEqual(exc_debug["during"], "{% partial undefined %}")
            self.assertEqual(exc_debug["line"], 2)
            self.assertEqual(exc_debug["name"], "partial_with_undefined_reference")
            self.assertIn("undefined", exc_debug["message"])

    @setup(
        {
            "existing_template": (
                "<h1>Header</h1><p>This template has no partials defined</p>"
            ),
        }
    )
    def test_undefined_partial_exception_info_template_does_not_exist(self):
        with self.assertRaises(TemplateDoesNotExist) as cm:
            self.engine.get_template("existing_template#undefined")

        self.assertIn("undefined", str(cm.exception))

    @setup(
        {
            "partial_with_syntax_error": (
                "<h1>Title</h1>\n"
                "{% partialdef syntax_error_partial %}\n"
                "    {% if user %}\n"
                "        <p>User: {{ user.name }}</p>\n"
                "    {% endif\n"
                "    <p>Missing closing tag above</p>\n"
                "{% endpartialdef %}\n"
                "{% partial syntax_error_partial %}\n"
            ),
        }
    )
    def test_partial_with_syntax_error_exception_info(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.engine.get_template("partial_with_syntax_error")

        self.assertIn("endif", str(cm.exception).lower())

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertIn("endpartialdef", exc_debug["during"])
            self.assertEqual(exc_debug["name"], "partial_with_syntax_error")
            self.assertIn("endif", exc_debug["message"].lower())

    @setup(
        {
            "partial_with_runtime_error": (
                "<h1>Title</h1>\n"
                "{% load bad_tag %}\n"
                "{% partialdef runtime_error_partial %}\n"
                "    <p>This will raise an error:</p>\n"
                "    {% badsimpletag %}\n"
                "{% endpartialdef %}\n"
                "{% partial runtime_error_partial %}\n"
            ),
        }
    )
    def test_partial_runtime_error_exception_info(self):
        template = self.engine.get_template("partial_with_runtime_error")
        context = Context()

        with self.assertRaises(RuntimeError) as cm:
            template.render(context)

        if self.engine.debug:
            exc_debug = cm.exception.template_debug

            self.assertIn("badsimpletag", exc_debug["during"])
            self.assertEqual(exc_debug["line"], 5)  # Line 5 is where badsimpletag is
            self.assertEqual(exc_debug["name"], "partial_with_runtime_error")
            self.assertIn("bad simpletag", exc_debug["message"])

    @setup(
        {
            "nested_partial_with_undefined_var": (
                "<h1>Title</h1>\n"
                "{% partialdef outer_partial %}\n"
                '    <div class="outer">\n'
                "        {% partialdef inner_partial %}\n"
                "            <p>{{ undefined_var }}</p>\n"
                "        {% endpartialdef %}\n"
                "        {% partial inner_partial %}\n"
                "    </div>\n"
                "{% endpartialdef %}\n"
                "{% partial outer_partial %}\n"
            ),
        }
    )
    def test_nested_partial_error_exception_info(self):
        template = self.engine.get_template("nested_partial_with_undefined_var")
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
            "parent.html": (
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<head>{% block title %}Default Title{% endblock %}</head>\n"
                "<body>\n"
                "    {% block content %}{% endblock %}\n"
                "</body>\n"
                "</html>\n"
            ),
            "child.html": (
                "{% extends 'parent.html' %}\n"
                "{% block content %}\n"
                "    {% partialdef content_partial %}\n"
                "        <p>{{ missing_variable|undefined_filter }}</p>\n"
                "    {% endpartialdef %}\n"
                "    {% partial content_partial %}\n"
                "{% endblock %}\n"
            ),
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
            "partial_broken_nesting": (
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
            self.engine.get_template("partial_broken_nesting")

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
            "partial_broken_nesting_mixed": (
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
            self.engine.get_template("partial_broken_nesting_mixed")

        self.assertIn("endpartialdef", str(cm.exception))
        self.assertIn("Invalid block tag", str(cm.exception))
        self.assertIn("'endpartialdef outer'", str(cm.exception))

        reporter = ExceptionReporter(None, cm.exception.__class__, cm.exception, None)
        traceback_data = reporter.get_traceback_data()

        exception_value = str(traceback_data.get("exception_value", ""))
        self.assertIn("Invalid block tag", exception_value)
        self.assertIn("'endpartialdef outer'", str(cm.exception))
