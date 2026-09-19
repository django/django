import os

from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template
from django.template.engine import Engine
from django.template.exceptions import TemplateSyntaxError
from django.test import SimpleTestCase, override_settings

from .utils import ROOT, TEMPLATE_DIR

OTHER_DIR = os.path.join(ROOT, "other_templates")


class EngineTest(SimpleTestCase):
    def test_repr_empty(self):
        engine = Engine()
        self.assertEqual(
            repr(engine),
            "<Engine: app_dirs=False debug=False loaders=[("
            "'django.template.loaders.cached.Loader', "
            "['django.template.loaders.filesystem.Loader'])] "
            "string_if_invalid='' file_charset='utf-8' builtins=["
            "'django.template.defaulttags', 'django.template.defaultfilters', "
            "'django.template.loader_tags'] autoescape=True>",
        )

    def test_repr(self):
        engine = Engine(
            dirs=[TEMPLATE_DIR],
            context_processors=["django.template.context_processors.debug"],
            debug=True,
            loaders=["django.template.loaders.filesystem.Loader"],
            string_if_invalid="x",
            file_charset="utf-16",
            libraries={"custom": "template_tests.templatetags.custom"},
            autoescape=False,
        )
        self.assertEqual(
            repr(engine),
            f"<Engine: dirs=[{TEMPLATE_DIR!r}] app_dirs=False "
            "context_processors=['django.template.context_processors.debug'] "
            "debug=True loaders=['django.template.loaders.filesystem.Loader'] "
            "string_if_invalid='x' file_charset='utf-16' "
            "libraries={'custom': 'template_tests.templatetags.custom'} "
            "builtins=['django.template.defaulttags', "
            "'django.template.defaultfilters', 'django.template.loader_tags'] "
            "autoescape=False>",
        )


class RenderToStringTest(SimpleTestCase):
    def setUp(self):
        self.engine = Engine(dirs=[TEMPLATE_DIR])

    def test_basic_context(self):
        self.assertEqual(
            self.engine.render_to_string("test_context.html", {"obj": "test"}),
            "obj:test\n",
        )

    def test_autoescape_off(self):
        engine = Engine(dirs=[TEMPLATE_DIR], autoescape=False)
        self.assertEqual(
            engine.render_to_string("test_context.html", {"obj": "<script>"}),
            "obj:<script>\n",
        )


class GetDefaultTests(SimpleTestCase):
    @override_settings(TEMPLATES=[])
    def test_no_engines_configured(self):
        msg = "No DjangoTemplates backend is configured."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            Engine.get_default()

    @override_settings(
        TEMPLATES=[
            {
                "NAME": "default",
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {"file_charset": "abc"},
            }
        ]
    )
    def test_single_engine_configured(self):
        self.assertEqual(Engine.get_default().file_charset, "abc")

    @override_settings(
        TEMPLATES=[
            {
                "NAME": "default",
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {"file_charset": "abc"},
            },
            {
                "NAME": "other",
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {"file_charset": "def"},
            },
        ]
    )
    def test_multiple_engines_configured(self):
        self.assertEqual(Engine.get_default().file_charset, "abc")


class LoaderTests(SimpleTestCase):
    def test_origin(self):
        engine = Engine(dirs=[TEMPLATE_DIR], debug=True)
        template = engine.get_template("index.html")
        self.assertEqual(template.origin.template_name, "index.html")

    def test_loader_priority(self):
        """
        #21460 -- The order of template loader works.
        """
        loaders = [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]
        engine = Engine(dirs=[OTHER_DIR, TEMPLATE_DIR], loaders=loaders)
        template = engine.get_template("priority/foo.html")
        self.assertEqual(template.render(Context()), "priority\n")

    def test_cached_loader_priority(self):
        """
        The order of template loader works. Refs #21460.
        """
        loaders = [
            (
                "django.template.loaders.cached.Loader",
                [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ],
            ),
        ]
        engine = Engine(dirs=[OTHER_DIR, TEMPLATE_DIR], loaders=loaders)

        template = engine.get_template("priority/foo.html")
        self.assertEqual(template.render(Context()), "priority\n")

        template = engine.get_template("priority/foo.html")
        self.assertEqual(template.render(Context()), "priority\n")


class RaiseOnMissingVariableTests(SimpleTestCase):
    """Tests for raise_on_missing_variable option in template engine (#28618)."""

    def test_default_behavior(self):
        """Missing variables use empty string by default."""
        engine = Engine()
        template = Template("Hello {{ missing }}!", engine=engine)
        self.assertEqual(template.render(Context({})), "Hello !")

    def test_string_if_invalid_replacement(self):
        """Missing variables use string_if_invalid when set."""
        engine = Engine(string_if_invalid="INVALID")
        template = Template("Hello {{ missing }}!", engine=engine)
        self.assertEqual(template.render(Context({})), "Hello INVALID!")

    def test_raise_missing_variable(self):
        """
        Missing variables use string_if_invalid when
        raise_on_missing_variable is True.
        """
        engine = Engine(raise_on_missing_variable=True)
        template = Template("Hello {{ missing }}!", engine=engine)
        # Even with raise_on_missing_variable=True, string_if_invalid is used
        self.assertEqual(template.render(Context({})), "Hello !")

    def test_nested_missing_variable(self):
        """
        Nested missing variables use string_if_invalid when
        raise_on_missing_variable is True.
        """
        engine = Engine(raise_on_missing_variable=True)
        template = Template("{{ user.name }}", engine=engine)
        # Even with raise_on_missing_variable=True, string_if_invalid is used
        self.assertEqual(template.render(Context({"user": {}})), "")

    def test_string_if_invalid_with_raise(self):
        """string_if_invalid is used even when raise_on_missing_variable is True."""
        engine = Engine(raise_on_missing_variable=True, string_if_invalid="INVALID")
        template = Template("{{ missing }}", engine=engine)
        self.assertEqual(template.render(Context({})), "INVALID")

    def test_not_silent_variable_failure(self):
        """Non-silent variable failures propagate normally."""

        class NonSilentVar:
            def __str__(self):
                raise AttributeError("Should propagate")

        engine = Engine(raise_on_missing_variable=True)
        template = Template("{{ var }}", engine=engine)
        with self.assertRaisesMessage(AttributeError, "Should propagate"):
            template.render(Context({"var": NonSilentVar()}))

    def test_syntax_error_not_suppressed(self):
        """Template syntax errors are not affected by raise_on_missing_variable."""
        engine = Engine(raise_on_missing_variable=True)
        with self.assertRaisesMessage(
            TemplateSyntaxError, "Unexpected end of expression in if tag."
        ):
            Template("{% if %}{% endif %}", engine=engine)
