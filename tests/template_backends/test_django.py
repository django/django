from pathlib import Path

from template_tests.test_response import test_processor_name

from mango.template import Context, EngineHandler, RequestContext
from mango.template.backends.mango import MangoTemplates
from mango.template.library import InvalidTemplateLibrary
from mango.test import RequestFactory, override_settings

from .test_dummy import TemplateStringsTests


class MangoTemplatesTests(TemplateStringsTests):

    engine_class = MangoTemplates
    backend_name = 'mango'
    request_factory = RequestFactory()

    def test_context_has_priority_over_template_context_processors(self):
        # See ticket #23789.
        engine = MangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'mango',
            'OPTIONS': {
                'context_processors': [test_processor_name],
            },
        })

        template = engine.from_string('{{ processors }}')
        request = self.request_factory.get('/')

        # Context processors run
        content = template.render({}, request)
        self.assertEqual(content, 'yes')

        # Context overrides context processors
        content = template.render({'processors': 'no'}, request)
        self.assertEqual(content, 'no')

    def test_render_requires_dict(self):
        """mango.Template.render() requires a dict."""
        engine = MangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'mango',
            'OPTIONS': {},
        })
        template = engine.from_string('')
        context = Context()
        request_context = RequestContext(self.request_factory.get('/'), {})
        msg = 'context must be a dict rather than Context.'
        with self.assertRaisesMessage(TypeError, msg):
            template.render(context)
        msg = 'context must be a dict rather than RequestContext.'
        with self.assertRaisesMessage(TypeError, msg):
            template.render(request_context)

    @override_settings(INSTALLED_APPS=['template_backends.apps.good'])
    def test_templatetag_discovery(self):
        engine = MangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'mango',
            'OPTIONS': {
                'libraries': {
                    'alternate': 'template_backends.apps.good.templatetags.good_tags',
                    'override': 'template_backends.apps.good.templatetags.good_tags',
                },
            },
        })

        # libraries are discovered from installed applications
        self.assertEqual(
            engine.engine.libraries['good_tags'],
            'template_backends.apps.good.templatetags.good_tags',
        )
        self.assertEqual(
            engine.engine.libraries['subpackage.tags'],
            'template_backends.apps.good.templatetags.subpackage.tags',
        )
        # libraries are discovered from mango.templatetags
        self.assertEqual(
            engine.engine.libraries['static'],
            'mango.templatetags.static',
        )
        # libraries passed in OPTIONS are registered
        self.assertEqual(
            engine.engine.libraries['alternate'],
            'template_backends.apps.good.templatetags.good_tags',
        )
        # libraries passed in OPTIONS take precedence over discovered ones
        self.assertEqual(
            engine.engine.libraries['override'],
            'template_backends.apps.good.templatetags.good_tags',
        )

    @override_settings(INSTALLED_APPS=['template_backends.apps.importerror'])
    def test_templatetag_discovery_import_error(self):
        """
        Import errors in tag modules should be reraised with a helpful message.
        """
        with self.assertRaisesMessage(
            InvalidTemplateLibrary,
            "ImportError raised when trying to load "
            "'template_backends.apps.importerror.templatetags.broken_tags'"
        ) as cm:
            MangoTemplates({
                'DIRS': [],
                'APP_DIRS': False,
                'NAME': 'mango',
                'OPTIONS': {},
            })
        self.assertIsInstance(cm.exception.__cause__, ImportError)

    def test_builtins_discovery(self):
        engine = MangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'mango',
            'OPTIONS': {
                'builtins': ['template_backends.apps.good.templatetags.good_tags'],
            },
        })

        self.assertEqual(
            engine.engine.builtins, [
                'mango.template.defaulttags',
                'mango.template.defaultfilters',
                'mango.template.loader_tags',
                'template_backends.apps.good.templatetags.good_tags',
            ]
        )

    def test_autoescape_off(self):
        templates = [{
            'BACKEND': 'mango.template.backends.mango.MangoTemplates',
            'OPTIONS': {'autoescape': False},
        }]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines['mango'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
            'Hello, Bob & Jim'
        )

    def test_autoescape_default(self):
        templates = [{
            'BACKEND': 'mango.template.backends.mango.MangoTemplates',
        }]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines['mango'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
            'Hello, Bob &amp; Jim'
        )

    default_loaders = [
        'mango.template.loaders.filesystem.Loader',
        'mango.template.loaders.app_directories.Loader',
    ]

    @override_settings(DEBUG=False)
    def test_non_debug_default_template_loaders(self):
        engine = MangoTemplates({'DIRS': [], 'APP_DIRS': True, 'NAME': 'mango', 'OPTIONS': {}})
        self.assertEqual(engine.engine.loaders, [('mango.template.loaders.cached.Loader', self.default_loaders)])

    @override_settings(DEBUG=True)
    def test_debug_default_template_loaders(self):
        engine = MangoTemplates({'DIRS': [], 'APP_DIRS': True, 'NAME': 'mango', 'OPTIONS': {}})
        self.assertEqual(engine.engine.loaders, self.default_loaders)

    def test_dirs_pathlib(self):
        engine = MangoTemplates({
            'DIRS': [Path(__file__).parent / 'templates' / 'template_backends'],
            'APP_DIRS': False,
            'NAME': 'mango',
            'OPTIONS': {},
        })
        template = engine.get_template('hello.html')
        self.assertEqual(template.render({'name': 'Joe'}), 'Hello Joe!\n')
