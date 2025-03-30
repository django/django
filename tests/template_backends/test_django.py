from pathlib import Path

from template_tests.test_response import test_processor_name

from django.template import Context, EngineHandler, RequestContext
from django.template.backends.django import DjangoTemplates
from django.template.library import InvalidTemplateLibrary
from django.test import RequestFactory, override_settings

from .test_dummy import TemplateStringsTests


class DjangoTemplatesTests(TemplateStringsTests):
    engine_class = DjangoTemplates
    backend_name = "django"
    request_factory = RequestFactory()

    def test_context_has_priority_over_template_context_processors(self):
        # See ticket #23789.
        engine = DjangoTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "django",
                "OPTIONS": {
                    "context_processors": [test_processor_name],
                },
            }
        )

        template = engine.from_string("{{ processors }}")
        request = self.request_factory.get("/")

        # Context processors run
        content = template.render({}, request)
        self.assertEqual(content, "yes")

        # Context overrides context processors
        content = template.render({"processors": "no"}, request)
        self.assertEqual(content, "no")

    def test_render_requires_dict(self):
        """django.Template.render() requires a dict."""
        engine = DjangoTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "django",
                "OPTIONS": {},
            }
        )
        template = engine.from_string("")
        context = Context()
        request_context = RequestContext(self.request_factory.get("/"), {})
        msg = "context must be a dict rather than Context."
        with self.assertRaisesMessage(TypeError, msg):
            template.render(context)
        msg = "context must be a dict rather than RequestContext."
        with self.assertRaisesMessage(TypeError, msg):
            template.render(request_context)

    @override_settings(INSTALLED_APPS=["template_backends.apps.good"])
    def test_templatetag_discovery(self):
        engine = DjangoTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "django",
                "OPTIONS": {
                    "libraries": {
                        "alternate": (
                            "template_backends.apps.good.templatetags.good_tags"
                        ),
                        "override": (
                            "template_backends.apps.good.templatetags.good_tags"
                        ),
                    },
                },
            }
        )

        # libraries are discovered from installed applications
        self.assertEqual(
            engine.engine.libraries["good_tags"],
            "template_backends.apps.good.templatetags.good_tags",
        )
        self.assertEqual(
            engine.engine.libraries["subpackage.tags"],
            "template_backends.apps.good.templatetags.subpackage.tags",
        )
        # libraries are discovered from django.templatetags
        self.assertEqual(
            engine.engine.libraries["static"],
            "django.templatetags.static",
        )
        # libraries passed in OPTIONS are registered
        self.assertEqual(
            engine.engine.libraries["alternate"],
            "template_backends.apps.good.templatetags.good_tags",
        )
        # libraries passed in OPTIONS take precedence over discovered ones
        self.assertEqual(
            engine.engine.libraries["override"],
            "template_backends.apps.good.templatetags.good_tags",
        )

    @override_settings(INSTALLED_APPS=["template_backends.apps.importerror"])
    def test_templatetag_discovery_import_error(self):
        """
        Import errors in tag modules should be reraised with a helpful message.
        """
        msg = (
            "ImportError raised when trying to load "
            "'template_backends.apps.importerror.templatetags.broken_tags'"
        )
        with self.assertRaisesMessage(InvalidTemplateLibrary, msg) as cm:
            DjangoTemplates(
                {
                    "DIRS": [],
                    "APP_DIRS": False,
                    "NAME": "django",
                    "OPTIONS": {},
                }
            )
        self.assertIsInstance(cm.exception.__cause__, ImportError)

    def test_builtins_discovery(self):
        engine = DjangoTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "django",
                "OPTIONS": {
                    "builtins": ["template_backends.apps.good.templatetags.good_tags"],
                },
            }
        )

        self.assertEqual(
            engine.engine.builtins,
            [
                "django.template.defaulttags",
                "django.template.defaultfilters",
                "django.template.loader_tags",
                "template_backends.apps.good.templatetags.good_tags",
            ],
        )

    def test_autoescape_off(self):
        templates = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {"autoescape": False},
            }
        ]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines["django"]
            .from_string("Hello, {{ name }}")
            .render({"name": "Bob & Jim"}),
            "Hello, Bob & Jim",
        )

    def test_autoescape_default(self):
        templates = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
            }
        ]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines["django"]
            .from_string("Hello, {{ name }}")
            .render({"name": "Bob & Jim"}),
            "Hello, Bob &amp; Jim",
        )

    def test_default_template_loaders(self):
        """The cached template loader is always enabled by default."""
        for debug in (True, False):
            with self.subTest(DEBUG=debug), self.settings(DEBUG=debug):
                engine = DjangoTemplates(
                    {"DIRS": [], "APP_DIRS": True, "NAME": "django", "OPTIONS": {}}
                )
                self.assertEqual(
                    engine.engine.loaders,
                    [
                        (
                            "django.template.loaders.cached.Loader",
                            [
                                "django.template.loaders.filesystem.Loader",
                                "django.template.loaders.app_directories.Loader",
                            ],
                        )
                    ],
                )

    def test_dirs_pathlib(self):
        engine = DjangoTemplates(
            {
                "DIRS": [Path(__file__).parent / "templates" / "template_backends"],
                "APP_DIRS": False,
                "NAME": "django",
                "OPTIONS": {},
            }
        )
        template = engine.get_template("hello.html")
        self.assertEqual(template.render({"name": "Joe"}), "Hello Joe!\n")
