from django.template import (
    Context,
    Engine,
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
                "{% partialdef test-partial inline invalid %}"
                "Content"
                "{% endpartialdef %}"
            )
        }
    )
    def test_partial_error06(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "partialdef tag requires 2-3 arguments"
        ):
            self.engine.get_template("partial-error06")

    @setup(
        {
            "partial-error07": (
                "{% partialdef testing-partial %}\n"
                "HERE IS THE TEST CONTENT\n"
                "{% endpartialdef invalid %}\n"
                "{% partial testing-partial %}"
            )
        }
    )
    def test_partial_error07(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string("partial-error07")

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

    def test_partial_runtime_exception_has_debug_info(self):
        buggy_template = """<h1>Title</h1>
{% partialdef test-partial %}
<p>{{ nonexistent|default:alsonotthere }}</p>
{% endpartialdef %}
<h2>Sub Title</h2>
{% partial test-partial %}
"""
        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": buggy_template},
                ),
            ],
        )
        template = engine.get_template("template")

        context = Context({})
        with self.assertRaises(VariableDoesNotExist) as cm:
            template.render(context)

        exc_info = cm.exception.template_debug

        self.assertEqual(exc_info["during"], "{{ nonexistent|default:alsonotthere }}")
        self.assertEqual(exc_info["line"], 3)
        self.assertEqual(exc_info["name"], "template")
        self.assertIn("Failed lookup", exc_info["message"])

    def test_partial_template_get_exception_info_delegation(self):
        template_content = """<h1>Title</h1>
{% partialdef test-partial %}
<p>Content</p>
{% endpartialdef %}
"""
        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": template_content},
                ),
            ],
        )
        template = engine.get_template("template")

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
        self.assertEqual(exc_info["name"], "template")
        self.assertEqual(exc_info["message"], "Test exception")

    def test_undefined_partial_exception_info(self):
        template_with_undefined = """<h1>Header</h1>
{% partial undefined-partial %}
<p>After undefined partial</p>
"""
        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": template_with_undefined},
                ),
            ],
        )

        template = engine.get_template("template")
        with self.assertRaises(TemplateSyntaxError) as cm:
            template.render(Context())

        self.assertIn("undefined-partial", str(cm.exception))
        self.assertIn("is not defined", str(cm.exception))

        exc_debug = cm.exception.template_debug

        self.assertEqual(exc_debug["during"], "{% partial undefined-partial %}")
        self.assertEqual(exc_debug["line"], 2)
        self.assertEqual(exc_debug["name"], "template")
        self.assertIn("undefined-partial", exc_debug["message"])

    def test_undefined_partial_exception_info_template_does_not_exist(self):
        template_with_no_partials = """<h1>Header</h1>
<p>This template has no partials defined</p>
"""
        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"existing_template": template_with_no_partials},
                ),
            ],
        )

        with self.assertRaises(TemplateDoesNotExist) as cm:
            engine.get_template("existing_template#undefined-partial")

        self.assertIn("undefined-partial", str(cm.exception))

    def test_partial_with_syntax_error_exception_info(self):
        template_with_syntax_error = """<h1>Title</h1>
{% partialdef syntax-error-partial %}
    {% if user %}
        <p>User: {{ user.name }}</p>
    {% endif
    <p>Missing closing tag above</p>
{% endpartialdef %}
{% partial syntax-error-partial %}
"""
        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": template_with_syntax_error},
                ),
            ],
        )

        with self.assertRaises(TemplateSyntaxError) as cm:
            engine.get_template("template")

        self.assertIn("endif", str(cm.exception).lower())

        exc_debug = cm.exception.template_debug

        self.assertIn("endpartialdef", exc_debug["during"])
        self.assertEqual(exc_debug["name"], "template")
        self.assertIn("endif", exc_debug["message"].lower())

    def test_partial_runtime_error_exception_info(self):
        template_with_runtime_error = """<h1>Title</h1>
{% load bad_tag %}
{% partialdef runtime-error-partial %}
    <p>This will raise an error:</p>
    {% badsimpletag %}
{% endpartialdef %}
{% partial runtime-error-partial %}
"""
        engine = Engine(
            debug=True,
            libraries={"bad_tag": "template_tests.templatetags.bad_tag"},
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": template_with_runtime_error},
                ),
            ],
        )

        template = engine.get_template("template")
        context = Context()

        with self.assertRaises(RuntimeError) as cm:
            template.render(context)

        exc_debug = cm.exception.template_debug

        self.assertIn("badsimpletag", exc_debug["during"])
        self.assertEqual(exc_debug["line"], 5)  # Line 5 is where badsimpletag is
        self.assertEqual(exc_debug["name"], "template")
        self.assertIn("bad simpletag", exc_debug["message"])

    def test_nested_partial_error_exception_info(self):
        template_with_nested = """<h1>Title</h1>
{% partialdef outer-partial %}
    <div class="outer">
        {% partialdef inner-partial %}
            <p>{{ undefined_var }}</p>
        {% endpartialdef %}
        {% partial inner-partial %}
    </div>
{% endpartialdef %}
{% partial outer-partial %}
"""
        engine = Engine(
            debug=True,
            string_if_invalid="INVALID[%s]",
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {"template": template_with_nested},
                ),
            ],
        )

        template = engine.get_template("template")
        # Since string_if_invalid is set, it won't raise but will show INVALID
        output = template.render(Context())
        self.assertIn("INVALID[undefined_var]", output)

    def test_partial_in_extended_template_error(self):
        parent_template = """<!DOCTYPE html>
<html>
<head>{% block title %}Default Title{% endblock %}</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
"""

        child_template = """{% extends "parent.html" %}
{% block content %}
    {% partialdef content-partial %}
        <p>{{ missing_variable|undefined_filter }}</p>
    {% endpartialdef %}
    {% partial content-partial %}
{% endblock %}
"""

        engine = Engine(
            debug=True,
            loaders=[
                (
                    "django.template.loaders.locmem.Loader",
                    {
                        "parent.html": parent_template,
                        "child.html": child_template,
                    },
                ),
            ],
        )

        with self.assertRaises(TemplateSyntaxError) as cm:
            engine.get_template("child.html")

        self.assertIn("undefined_filter", str(cm.exception))

        exc_debug = cm.exception.template_debug

        self.assertIn("undefined_filter", exc_debug["during"])
        self.assertEqual(exc_debug["name"], "child.html")
        self.assertIn("undefined_filter", exc_debug["message"])
