import os
from unittest import mock

from django.http import HttpResponse
from django.template import (
    Context,
    Origin,
    Template,
    TemplateDoesNotExist,
    TemplateSyntaxError,
    engines,
)
from django.template.backends.django import DjangoTemplates
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import path, reverse

engine = engines["django"]


class PartialTagsTests(TestCase):

    def test_invalid_template_name_raises_template_does_not_exist(self):
        for template_name in [123, None, "", "#", "#name"]:
            with (
                self.subTest(template_name=template_name),
                self.assertRaisesMessage(TemplateDoesNotExist, str(template_name)),
            ):
                engine.get_template(template_name)

    def test_template_source_is_correct(self):
        partial = engine.get_template("partial_examples.html#test-partial")
        self.assertEqual(
            partial.template.source,
            "{% partialdef test-partial %}\nTEST-PARTIAL-CONTENT\n{% endpartialdef %}",
        )

    def test_template_source_inline_is_correct(self):
        partial = engine.get_template("partial_examples.html#inline-partial")
        self.assertEqual(
            partial.template.source,
            "{% partialdef inline-partial inline %}\nINLINE-CONTENT\n"
            "{% endpartialdef %}",
        )

    def test_full_template_from_loader(self):
        template = engine.get_template("partial_examples.html")
        rendered = template.render({})

        # Check the partial was rendered twice
        self.assertEqual(2, rendered.count("TEST-PARTIAL-CONTENT"))
        self.assertEqual(1, rendered.count("INLINE-CONTENT"))

    def test_chained_exception_forwarded(self):
        with self.assertRaises(TemplateDoesNotExist) as ctx:
            engine.get_template("not_there.html#not-a-partial")

        exception = ctx.exception
        self.assertGreater(len(exception.tried), 0)
        origin, _ = exception.tried[0]
        self.assertEqual(origin.template_name, "not_there.html")

    def test_partials_use_cached_loader_when_configured(self):
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        backend = DjangoTemplates(
            {
                "NAME": "django",
                "DIRS": [template_dir],
                "APP_DIRS": False,
                "OPTIONS": {
                    "loaders": [
                        (
                            "django.template.loaders.cached.Loader",
                            ["django.template.loaders.filesystem.Loader"],
                        ),
                    ],
                },
            }
        )
        cached_loader = backend.engine.template_loaders[0]
        filesystem_loader = cached_loader.loaders[0]

        with mock.patch.object(
            filesystem_loader, "get_contents", wraps=filesystem_loader.get_contents
        ) as mock_get_contents:
            full_template = backend.get_template("partial_examples.html")
            self.assertIn("TEST-PARTIAL-CONTENT", full_template.render({}))

            partial_template = backend.get_template(
                "partial_examples.html#test-partial"
            )
            self.assertEqual(
                "TEST-PARTIAL-CONTENT", partial_template.render({}).strip()
            )

            mock_get_contents.assert_called_once()

    def test_context_available_in_response_for_partial_template(self):
        def sample_view(request):
            return HttpResponse(
                render_to_string("partial_examples.html#test-partial", {"foo": "bar"})
            )

        class PartialUrls:
            urlpatterns = [path("sample/", sample_view, name="sample-view")]

        with override_settings(ROOT_URLCONF=PartialUrls):
            response = self.client.get(reverse("sample-view"))

        self.assertContains(response, "TEST-PARTIAL-CONTENT")
        self.assertEqual(response.context.get("foo"), "bar")

    def test_response_with_multiple_parts(self):
        context = {}
        template_partials = ["partial_child.html", "partial_child.html#extra-content"]

        response_whole_content_at_once = HttpResponse(
            "".join(
                render_to_string(template_name, context)
                for template_name in template_partials
            )
        )

        response_with_multiple_writes = HttpResponse()
        for template_name in template_partials:
            response_with_multiple_writes.write(
                render_to_string(template_name, context)
            )

        response_with_generator = HttpResponse(
            render_to_string(template_name, context)
            for template_name in template_partials
        )

        for label, response in [
            ("response_whole_content_at_once", response_whole_content_at_once),
            ("response_with_multiple_writes", response_with_multiple_writes),
            ("response_with_generator", response_with_generator),
        ]:
            with self.subTest(response=label):
                self.assertIn(b"Main Content", response.content)
                self.assertIn(b"Extra Content", response.content)

    def test_partial_engine_assignment_with_real_template(self):
        template_with_partial = engine.get_template(
            "partial_examples.html#test-partial"
        )
        self.assertEqual(template_with_partial.template.engine, engine.engine)
        rendered_content = template_with_partial.render({})
        self.assertEqual("TEST-PARTIAL-CONTENT", rendered_content.strip())


class RobustPartialHandlingTests(TestCase):

    def override_get_template(self, **kwargs):
        class TemplateWithCustomAttrs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

            def render(self, context):
                return "rendered content"

        template = TemplateWithCustomAttrs(**kwargs)
        origin = self.id()
        return mock.patch.object(
            engine.engine,
            "find_template",
            return_value=(template, origin),
        )

    def test_template_without_extra_data_attribute(self):
        partial_name = "some_partial_name"
        with (
            self.override_get_template(),
            self.assertRaisesMessage(TemplateDoesNotExist, partial_name),
        ):
            engine.get_template(f"some_template.html#{partial_name}")

    def test_template_extract_extra_data_robust(self):
        partial_name = "some_partial_name"
        for extra_data in (
            None,
            0,
            [],
            {},
            {"wrong-key": {}},
            {"partials": None},
            {"partials": {}},
            {"partials": []},
            {"partials": 0},
        ):
            with (
                self.subTest(extra_data=extra_data),
                self.override_get_template(extra_data=extra_data),
                self.assertRaisesMessage(TemplateDoesNotExist, partial_name),
            ):
                engine.get_template(f"template.html#{partial_name}")

    def test_nested_partials_rendering_with_context(self):
        template_source = """
        {% partialdef outer inline %}
            Hello {{ name }}!
            {% partialdef inner inline %}
                Your age is {{ age }}.
            {% endpartialdef inner %}
            Nice to meet you.
        {% endpartialdef outer %}
        """
        template = Template(template_source, origin=Origin(name="template.html"))

        context = Context({"name": "Alice", "age": 25})
        rendered = template.render(context)

        self.assertIn("Hello Alice!", rendered)
        self.assertIn("Your age is 25.", rendered)
        self.assertIn("Nice to meet you.", rendered)


class FindPartialSourceTests(TestCase):

    def test_find_partial_source_success(self):
        template = engine.get_template("partial_examples.html").template
        partial_proxy = template.extra_data["partials"]["test-partial"]

        expected = """{% partialdef test-partial %}
TEST-PARTIAL-CONTENT
{% endpartialdef %}"""
        self.assertEqual(partial_proxy.source.strip(), expected.strip())

    def test_find_partial_source_with_inline(self):
        template = engine.get_template("partial_examples.html").template
        partial_proxy = template.extra_data["partials"]["inline-partial"]

        expected = """{% partialdef inline-partial inline %}
INLINE-CONTENT
{% endpartialdef %}"""
        self.assertEqual(partial_proxy.source.strip(), expected.strip())

    def test_find_partial_source_nonexistent_partial(self):
        template = engine.get_template("partial_examples.html").template
        partial_proxy = template.extra_data["partials"]["test-partial"]

        result = partial_proxy.find_partial_source(
            template.source, "nonexistent-partial"
        )
        self.assertEqual(result, "")

    def test_find_partial_source_empty_partial(self):
        template_source = "{% partialdef empty %}{% endpartialdef %}"
        template = Template(template_source)
        partial_proxy = template.extra_data["partials"]["empty"]

        result = partial_proxy.find_partial_source(template_source, "empty")
        self.assertEqual(result, "{% partialdef empty %}{% endpartialdef %}")

    def test_find_partial_source_multiple_consecutive_partials(self):

        template_source = (
            "{% partialdef empty %}{% endpartialdef %}"
            "{% partialdef other %}...{% endpartialdef %}"
        )
        template = Template(template_source)

        empty_proxy = template.extra_data["partials"]["empty"]
        other_proxy = template.extra_data["partials"]["other"]

        empty_result = empty_proxy.find_partial_source(template_source, "empty")
        self.assertEqual(empty_result, "{% partialdef empty %}{% endpartialdef %}")

        other_result = other_proxy.find_partial_source(template_source, "other")
        self.assertEqual(other_result, "{% partialdef other %}...{% endpartialdef %}")

    def test_partials_with_duplicate_names(self):
        test_cases = [
            (
                "nested",
                """
                {% partialdef duplicate %}{% partialdef duplicate %}
                CONTENT
                {% endpartialdef %}{% endpartialdef %}
                """,
            ),
            (
                "conditional",
                """
                {% if ... %}
                  {% partialdef duplicate %}
                  CONTENT
                  {% endpartialdef %}
                {% else %}
                  {% partialdef duplicate %}
                  OTHER-CONTENT
                  {% endpartialdef %}
                {% endif %}
                """,
            ),
        ]

        for test_name, template_source in test_cases:
            with self.subTest(test_name=test_name):
                with self.assertRaisesMessage(
                    TemplateSyntaxError,
                    "Partial 'duplicate' is already defined in the "
                    "'template.html' template.",
                ):
                    Template(template_source, origin=Origin(name="template.html"))

    def test_find_partial_source_supports_named_end_tag(self):
        template_source = "{% partialdef thing %}CONTENT{% endpartialdef thing %}"
        template = Template(template_source)
        partial_proxy = template.extra_data["partials"]["thing"]

        result = partial_proxy.find_partial_source(template_source, "thing")
        self.assertEqual(
            result, "{% partialdef thing %}CONTENT{% endpartialdef thing %}"
        )

    def test_find_partial_source_supports_nested_partials(self):
        template_source = (
            "{% partialdef outer %}"
            "{% partialdef inner %}...{% endpartialdef %}"
            "{% endpartialdef %}"
        )
        template = Template(template_source)

        empty_proxy = template.extra_data["partials"]["outer"]
        other_proxy = template.extra_data["partials"]["inner"]

        outer_result = empty_proxy.find_partial_source(template_source, "outer")
        self.assertEqual(
            outer_result,
            (
                "{% partialdef outer %}{% partialdef inner %}"
                "...{% endpartialdef %}{% endpartialdef %}"
            ),
        )

        inner_result = other_proxy.find_partial_source(template_source, "inner")
        self.assertEqual(inner_result, "{% partialdef inner %}...{% endpartialdef %}")

    def test_find_partial_source_supports_nested_partials_and_named_end_tags(self):
        template_source = (
            "{% partialdef outer %}"
            "{% partialdef inner %}...{% endpartialdef inner %}"
            "{% endpartialdef outer %}"
        )
        template = Template(template_source)

        empty_proxy = template.extra_data["partials"]["outer"]
        other_proxy = template.extra_data["partials"]["inner"]

        outer_result = empty_proxy.find_partial_source(template_source, "outer")
        self.assertEqual(
            outer_result,
            (
                "{% partialdef outer %}{% partialdef inner %}"
                "...{% endpartialdef inner %}{% endpartialdef outer %}"
            ),
        )

        inner_result = other_proxy.find_partial_source(template_source, "inner")
        self.assertEqual(
            inner_result, "{% partialdef inner %}...{% endpartialdef inner %}"
        )

    def test_find_partial_source_supports_nested_partials_and_mixed_end_tags_1(self):
        template_source = (
            "{% partialdef outer %}"
            "{% partialdef inner %}...{% endpartialdef %}"
            "{% endpartialdef outer %}"
        )
        template = Template(template_source)

        empty_proxy = template.extra_data["partials"]["outer"]
        other_proxy = template.extra_data["partials"]["inner"]

        outer_result = empty_proxy.find_partial_source(template_source, "outer")
        self.assertEqual(
            outer_result,
            (
                "{% partialdef outer %}{% partialdef inner %}"
                "...{% endpartialdef %}{% endpartialdef outer %}"
            ),
        )

        inner_result = other_proxy.find_partial_source(template_source, "inner")
        self.assertEqual(inner_result, "{% partialdef inner %}...{% endpartialdef %}")

    def test_find_partial_source_supports_nested_partials_and_mixed_end_tags_2(self):
        template_source = (
            "{% partialdef outer %}"
            "{% partialdef inner %}...{% endpartialdef inner %}"
            "{% endpartialdef %}"
        )
        template = Template(template_source)

        empty_proxy = template.extra_data["partials"]["outer"]
        other_proxy = template.extra_data["partials"]["inner"]

        outer_result = empty_proxy.find_partial_source(template_source, "outer")
        self.assertEqual(
            outer_result,
            (
                "{% partialdef outer %}{% partialdef inner %}"
                "...{% endpartialdef inner %}{% endpartialdef %}"
            ),
        )

        inner_result = other_proxy.find_partial_source(template_source, "inner")
        self.assertEqual(
            inner_result, "{% partialdef inner %}...{% endpartialdef inner %}"
        )
