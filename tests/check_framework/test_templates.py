from copy import deepcopy
from itertools import chain

from django.core.checks import Error, Warning
from django.core.checks.templates import check_templates
from django.template import engines
from django.template.backends.base import BaseEngine
from django.test import SimpleTestCase
from django.test.utils import override_settings


class ErrorEngine(BaseEngine):
    def __init__(self, params):
        params.pop("OPTIONS")
        super().__init__(params)

    def check(self, **kwargs):
        return [Error("Example")]


class CheckTemplatesTests(SimpleTestCase):
    @override_settings(
        TEMPLATES=[
            {"BACKEND": f"{__name__}.{ErrorEngine.__qualname__}", "NAME": "backend_1"},
            {"BACKEND": f"{__name__}.{ErrorEngine.__qualname__}", "NAME": "backend_2"},
        ]
    )
    def test_errors_aggregated(self):
        errors = check_templates(None)
        self.assertEqual(errors, [Error("Example")] * 2)


class CheckTemplateStringIfInvalidTest(SimpleTestCase):
    TEMPLATES_STRING_IF_INVALID = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "NAME": "backend_1",
            "OPTIONS": {
                "string_if_invalid": False,
            },
        },
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "NAME": "backend_2",
            "OPTIONS": {
                "string_if_invalid": 42,
            },
        },
    ]

    def _get_error_for_engine(self, engine):
        value = engine.engine.string_if_invalid
        return Error(
            "'string_if_invalid' in TEMPLATES OPTIONS must be a string but got: %r "
            "(%s)." % (value, type(value)),
            obj=engine,
            id="templates.E002",
        )

    def _check_engines(self, engines):
        return list(
            chain.from_iterable(e._check_string_if_invalid_is_string() for e in engines)
        )

    @override_settings(TEMPLATES=TEMPLATES_STRING_IF_INVALID)
    def test_string_if_invalid_not_string(self):
        _engines = engines.all()
        errors = [
            self._get_error_for_engine(_engines[0]),
            self._get_error_for_engine(_engines[1]),
        ]
        self.assertEqual(self._check_engines(_engines), errors)

    def test_string_if_invalid_first_is_string(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = "test"
        with self.settings(TEMPLATES=TEMPLATES):
            _engines = engines.all()
            errors = [self._get_error_for_engine(_engines[1])]
            self.assertEqual(self._check_engines(_engines), errors)

    def test_string_if_invalid_both_are_strings(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = "test"
        TEMPLATES[1]["OPTIONS"]["string_if_invalid"] = "test"
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self._check_engines(engines.all()), [])

    def test_string_if_invalid_not_specified(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        del TEMPLATES[1]["OPTIONS"]["string_if_invalid"]
        with self.settings(TEMPLATES=TEMPLATES):
            _engines = engines.all()
            errors = [self._get_error_for_engine(_engines[0])]
            self.assertEqual(self._check_engines(_engines), errors)


class CheckTemplateTagLibrariesWithSameName(SimpleTestCase):
    def get_settings(self, module_name, module_path, name="django"):
        return {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "NAME": name,
            "OPTIONS": {
                "libraries": {
                    module_name: f"check_framework.template_test_apps.{module_path}",
                },
            },
        }

    def _get_error_for_engine(self, engine, modules):
        return Warning(
            f"'same_tags' is used for multiple template tag modules: {modules}",
            obj=engine,
            id="templates.W003",
        )

    def _check_engines(self, engines):
        return list(
            chain.from_iterable(
                e._check_for_template_tags_with_the_same_name() for e in engines
            )
        )

    @override_settings(
        INSTALLED_APPS=[
            "check_framework.template_test_apps.same_tags_app_1",
            "check_framework.template_test_apps.same_tags_app_2",
        ]
    )
    def test_template_tags_with_same_name(self):
        _engines = engines.all()
        modules = (
            "'check_framework.template_test_apps.same_tags_app_1.templatetags"
            ".same_tags', 'check_framework.template_test_apps.same_tags_app_2"
            ".templatetags.same_tags'"
        )
        errors = [self._get_error_for_engine(_engines[0], modules)]
        self.assertEqual(self._check_engines(_engines), errors)

    def test_template_tags_for_separate_backends(self):
        # The "libraries" names are the same, but the backends are different.
        with self.settings(
            TEMPLATES=[
                self.get_settings(
                    "same_tags",
                    "same_tags_app_1.templatetags.same_tags",
                    name="backend_1",
                ),
                self.get_settings(
                    "same_tags",
                    "same_tags_app_2.templatetags.same_tags",
                    name="backend_2",
                ),
            ]
        ):
            self.assertEqual(self._check_engines(engines.all()), [])

    @override_settings(
        INSTALLED_APPS=["check_framework.template_test_apps.same_tags_app_1"]
    )
    def test_template_tags_same_library_in_installed_apps_libraries(self):
        with self.settings(
            TEMPLATES=[
                self.get_settings(
                    "same_tags", "same_tags_app_1.templatetags.same_tags"
                ),
            ]
        ):
            self.assertEqual(self._check_engines(engines.all()), [])

    @override_settings(
        INSTALLED_APPS=["check_framework.template_test_apps.same_tags_app_1"]
    )
    def test_template_tags_with_same_library_name_and_module_name(self):
        modules = (
            "'check_framework.template_test_apps.different_tags_app.templatetags"
            ".different_tags', 'check_framework.template_test_apps.same_tags_app_1"
            ".templatetags.same_tags'"
        )
        with self.settings(
            TEMPLATES=[
                self.get_settings(
                    "same_tags", "different_tags_app.templatetags.different_tags"
                ),
            ]
        ):
            _engines = engines.all()
            errors = [self._get_error_for_engine(_engines[0], modules)]
            self.assertEqual(self._check_engines(_engines), errors)

    def test_template_tags_with_different_library_name(self):
        with self.settings(
            TEMPLATES=[
                self.get_settings(
                    "same_tags",
                    "same_tags_app_1.templatetags.same_tags",
                    name="backend_1",
                ),
                self.get_settings(
                    "not_same_tags",
                    "same_tags_app_2.templatetags.same_tags",
                    name="backend_2",
                ),
            ]
        ):
            self.assertEqual(self._check_engines(engines.all()), [])

    @override_settings(
        INSTALLED_APPS=[
            "check_framework.template_test_apps.same_tags_app_1",
            "check_framework.template_test_apps.different_tags_app",
        ]
    )
    def test_template_tags_with_different_name(self):
        self.assertEqual(self._check_engines(engines.all()), [])
