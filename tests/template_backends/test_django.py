from template_tests.test_response import test_processor_name

from django.core.exceptions import ImproperlyConfigured
from django.template import EngineHandler
from django.template.backends.django import DjangoTemplates
from django.template.library import InvalidTemplateLibrary
from django.test import RequestFactory, override_settings

from .test_dummy import TemplateStringsTests


class DjangoTemplatesTests(TemplateStringsTests):

    engine_class = DjangoTemplates
    backend_name = 'django'

    def test_context_has_priority_over_template_context_processors(self):
        # See ticket #23789.
        engine = DjangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'django',
            'OPTIONS': {
                'context_processors': [test_processor_name],
            },
        })

        template = engine.from_string('{{ processors }}')
        request = RequestFactory().get('/')

        # Context processors run
        content = template.render({}, request)
        self.assertEqual(content, 'yes')

        # Context overrides context processors
        content = template.render({'processors': 'no'}, request)
        self.assertEqual(content, 'no')

    @override_settings(INSTALLED_APPS=['template_backends.apps.good'])
    def test_templatetag_discovery(self):
        engine = DjangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'django',
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
        # libraries are discovered from django.templatetags
        self.assertEqual(
            engine.engine.libraries['static'],
            'django.templatetags.static',
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
        ):
            DjangoTemplates({
                'DIRS': [],
                'APP_DIRS': False,
                'NAME': 'django',
                'OPTIONS': {},
            })

    def test_builtins_discovery(self):
        engine = DjangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'django',
            'OPTIONS': {
                'builtins': ['template_backends.apps.good.templatetags.good_tags'],
            },
        })

        self.assertEqual(
            engine.engine.builtins, [
                'django.template.defaulttags',
                'django.template.defaultfilters',
                'django.template.loader_tags',
                'template_backends.apps.good.templatetags.good_tags',
            ]
        )

    def test_autoescape_off(self):
        templates = [{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {'autoescape': False},
        }]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines['django'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
            'Hello, Bob & Jim'
        )

    def test_autoescape_default(self):
        templates = [{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
        }]
        engines = EngineHandler(templates=templates)
        self.assertEqual(
            engines['django'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
            'Hello, Bob &amp; Jim'
        )

    default_loaders = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]

    @override_settings(DEBUG=False)
    def test_non_debug_default_template_loaders(self):
        engine = DjangoTemplates({'DIRS': [], 'APP_DIRS': True, 'NAME': 'django', 'OPTIONS': {}})
        self.assertEqual(engine.engine.loaders, [('django.template.loaders.cached.Loader', self.default_loaders)])

    @override_settings(DEBUG=True)
    def test_debug_default_template_loaders(self):
        engine = DjangoTemplates({'DIRS': [], 'APP_DIRS': True, 'NAME': 'django', 'OPTIONS': {}})
        self.assertEqual(engine.engine.loaders, self.default_loaders)

    @override_settings(DEBUG=True)
    def test_debug_template_loaders_with_dirs(self):
        engine = DjangoTemplates({
            'DIRS': ['dirs'],
            'APP_DIRS': True,
            'NAME': 'django',
            'OPTIONS': {},
            'POST_APP_DIRS': ['post_app_dirs'],
        })
        self.assertEqual(engine.dirs, ['dirs'])
        self.assertEqual(
            engine.engine.loaders, [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                ('django.template.loaders.filesystem.Loader', ['post_app_dirs']),
            ]
        )

    def test_post_app_dir_incompatible_with_loaders(self):
        msg = 'post_app_dirs must not be set when loaders is defined.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DjangoTemplates({
                'DIRS': [],
                'APP_DIRS': False,
                'NAME': 'django',
                'OPTIONS': {'loaders': ['django.template.loaders.filesystem.Loader']},
                'POST_APP_DIRS': ['post_app_dirs'],
            })
