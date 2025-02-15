from pathlib import Path

from template_tests.test_response import test_processor_name

from thibaud.template import Context, EngineHandler, RequestContext
from thibaud.template.backends.thibaud import ThibaudTemplates
from thibaud.template.library import InvalidTemplateLibrary
from thibaud.test import RequestFactory, override_settings

from .test_dummy import TemplateStringsTests


class ThibaudTemplatesTests(TemplateStringsTests):
    engine_class = ThibaudTemplates
    backend_name = "thibaud"
    request_factory = RequestFactory()

    def test_context_has_priority_over_template_context_processors(self):
        # See ticket #23789.
        engine = ThibaudTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "thibaud",
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
        """thibaud.Template.render() requires a dict."""
        engine = ThibaudTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "thibaud",
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
        engine = ThibaudTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "thibaud",
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
        # libraries are discovered from thibaud.templatetags
        self.assertEqual(
            engine.engine.libraries["static"],
            "thibaud.templatetags.static",
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
        with self.assertRaisesMessage(
            InvalidTemplateLibrary,
            "ImportError raised when trying to load "
            "'template_backends.apps.importerror.templatetags.broken_tags'",
        ) as cm:
            ThibaudTemplates(
                {
                    "DIRS": [],
                    "APP_DIRS": False,
                    "NAME": "thibaud",
                    "OPTIONS": {},
                }
            )
        self.assertIsInstance(cm.exception.__cause__, ImportError)

    def test_builtins_discovery(self):
        engine = ThibaudTemplates(
            {
                "DIRS": [],
                "APP_DIRS": False,
                "NAME": "thibaud",
                "OPTIONS": {
                    "builtins": ["template_backends.apps.good.templatetags.good_tags"],
                },
            }
        )

        self.assertEqual(
            engine.engine.builtins,
            [
                "thibaud.template.defaulttags",
                "thibaud.template.defaultfilters",
                "thibaud.template.loader_tags",
                "template_backends.apps.good.templatetags.good_tags",
            ],
        )

    def test_autoescape_off(self):
        templates = [
            {
                "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
                "OPTIONS": {"autoescape": False},
            }
        ]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines["thibaud"]
            .from_string("Hello, {{ name }}")
            .render({"name": "Bob & Jim"}),
            "Hello, Bob & Jim",
        )

    def test_autoescape_default(self):
        templates = [
            {
                "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
            }
        ]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines["thibaud"]
            .from_string("Hello, {{ name }}")
            .render({"name": "Bob & Jim"}),
            "Hello, Bob &amp; Jim",
        )

    def test_default_template_loaders(self):
        """The cached template loader is always enabled by default."""
        for debug in (True, False):
            with self.subTest(DEBUG=debug), self.settings(DEBUG=debug):
                engine = ThibaudTemplates(
                    {"DIRS": [], "APP_DIRS": True, "NAME": "thibaud", "OPTIONS": {}}
                )
                self.assertEqual(
                    engine.engine.loaders,
                    [
                        (
                            "thibaud.template.loaders.cached.Loader",
                            [
                                "thibaud.template.loaders.filesystem.Loader",
                                "thibaud.template.loaders.app_directories.Loader",
                            ],
                        )
                    ],
                )

    def test_dirs_pathlib(self):
        engine = ThibaudTemplates(
            {
                "DIRS": [Path(__file__).parent / "templates" / "template_backends"],
                "APP_DIRS": False,
                "NAME": "thibaud",
                "OPTIONS": {},
            }
        )
        template = engine.get_template("hello.html")
        self.assertEqual(template.render({"name": "Joe"}), "Hello Joe!\n")
