import os
from types import ModuleType
from unittest import mock

from django.http import HttpResponse
from django.template import TemplateDoesNotExist, engines
from django.template.backends.django import DjangoTemplates
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import path, reverse


class PartialTagsTestCase(TestCase):

    @property
    def engine(self):
        return engines["django"]

    def test_invalid_name_raises_template_does_not_exist(self):
        for template_name in [123, None, "", "#", "#name"]:
            with (
                self.subTest(template_name=template_name),
                self.assertRaisesMessage(TemplateDoesNotExist, str(template_name)),
            ):
                self.engine.get_template(template_name)

    def test_template_source(self):
        partial = self.engine.get_template("partial_examples.html#test-partial")
        self.assertEqual(
            partial.template.source,
            "{% partialdef test-partial %}\nTEST-PARTIAL-CONTENT\n{% endpartialdef %}",
        )
        partial = self.engine.get_template("partial_examples.html#inline-partial")
        self.assertEqual(
            partial.template.source,
            "{% partialdef inline-partial inline %}\nINLINE-CONTENT\n"
            "{% endpartialdef %}",
        )

    def test_full_template_from_loader(self):
        template = self.engine.get_template("partial_examples.html")
        rendered = template.render({})

        # Check the partial was rendered twice
        self.assertEqual(2, rendered.count("TEST-PARTIAL-CONTENT"))
        self.assertEqual(1, rendered.count("INLINE-CONTENT"))

    def test_chained_exception_forwarded(self):
        with self.assertRaises(TemplateDoesNotExist) as ex:
            self.engine.get_template("not_there.html#not-a-partial")

        self.assertTrue(len(ex.exception.tried) > 0)
        origin, _ = ex.exception.tried[0]
        self.assertEqual(origin.template_name, "not_there.html")


class PartialTagsCacheTestCase(TestCase):
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
            rendered_full = full_template.render({})
            self.assertIn("TEST-PARTIAL-CONTENT", rendered_full)

            partial_template = backend.get_template(
                "partial_examples.html#test-partial"
            )
            rendered_partial = partial_template.render({})
            self.assertEqual("TEST-PARTIAL-CONTENT", rendered_partial.strip())

            mock_get_contents.assert_called_once()


class ResponseContextWithPartialTests(TestCase):

    def test_response_context_available_for_partial_template(self):
        def sample_view(request):

            return HttpResponse(
                render_to_string("partial_examples.html#test-partial", {"foo": "bar"})
            )

        urls_module = ModuleType("partial_test_urls")
        urls_module.urlpatterns = [path("sample/", sample_view, name="sample-view")]

        with override_settings(ROOT_URLCONF=urls_module):
            response = self.client.get(reverse("sample-view"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context)
        self.assertEqual(response.context["foo"], "bar")


class ResponseWithMultiplePartsTests(TestCase):
    def test_response_with_multiple_parts(self):
        context = {}
        template_partials = ["partial_child.html", "partial_child.html#extra-content"]

        response_content = ""
        for template_name in template_partials:
            response_content += render_to_string(template_name, context)

        response1 = HttpResponse(response_content)

        response2 = HttpResponse()
        for template_name in template_partials:
            response2.write(render_to_string(template_name, context))

        response3 = HttpResponse(
            render_to_string(template_name, context)
            for template_name in template_partials
        )

        for response in [response1, response2, response3]:
            self.assertIn(b"Main Content", response.content)
            self.assertIn(b"Extra Content", response.content)


class RobustPartialHandlingTest(TestCase):

    @property
    def engine(self):
        return engines["django"]

    def test_template_without_extra_data_attribute(self):

        class TemplateWithoutExtraData:
            def render(self, context):
                return "rendered content"

        with mock.patch.object(
            self.engine.engine, "get_template", return_value=TemplateWithoutExtraData()
        ):
            with self.assertRaises(TemplateDoesNotExist):
                self.engine.get_template("some_template.html#some_partial")

    def test_template_with_non_dict_extra_data(self):

        class TemplateWithInvalidExtraData:
            def __init__(self, extra_data):
                self.extra_data = extra_data

            def render(self, context):
                return "rendered content"

        with mock.patch.object(
            self.engine.engine,
            "get_template",
            return_value=TemplateWithInvalidExtraData(None),
        ):
            with self.assertRaises(TemplateDoesNotExist):
                self.engine.get_template("template.html#partial")

    def test_template_with_non_dict_partial_contents(self):

        class TemplateWithInvalidPartialContents:
            def __init__(self, partial_contents):
                self.extra_data = {"template-partials": partial_contents}

            def render(self, context):
                return "rendered content"

        with mock.patch.object(
            self.engine.engine,
            "get_template",
            return_value=TemplateWithInvalidPartialContents(None),
        ):
            with self.assertRaises(TemplateDoesNotExist):
                self.engine.get_template("template.html#partial")

    def test_partial_engine_assignment_with_real_template(self):

        template_with_partial = self.engine.get_template(
            "partial_examples.html#test-partial"
        )
        self.assertEqual(template_with_partial.template.engine, self.engine.engine)
        rendered_content = template_with_partial.render({})
        self.assertEqual("TEST-PARTIAL-CONTENT", rendered_content.strip())


class FindPartialSourceTest(TestCase):
    """Test the find_partial_source method of PartialTemplate"""

    def setUp(self):
        self.engine = engines["django"]

    def test_find_partial_source_success(self):
        template = self.engine.get_template("partial_examples.html")
        partial_proxy = template.template.extra_data["template-partials"][
            "test-partial"
        ]

        result = partial_proxy.source

        expected = """{% partialdef test-partial %}
TEST-PARTIAL-CONTENT
{% endpartialdef %}"""
        self.assertEqual(result.strip(), expected.strip())

    def test_find_partial_source_with_inline(self):
        template = self.engine.get_template("partial_examples.html")
        partial_proxy = template.template.extra_data["template-partials"][
            "inline-partial"
        ]

        result = partial_proxy.source

        expected = """{% partialdef inline-partial inline %}
INLINE-CONTENT
{% endpartialdef %}"""
        self.assertEqual(result.strip(), expected.strip())

    def test_find_partial_source_nonexistent_partial(self):
        template = self.engine.get_template("partial_examples.html")
        partial_proxy = template.template.extra_data["template-partials"][
            "test-partial"
        ]

        result = partial_proxy.find_partial_source(
            template.template.source, "nonexistent-partial"
        )

        self.assertEqual(result, "")
