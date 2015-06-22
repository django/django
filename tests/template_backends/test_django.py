from template_tests.test_response import test_processor_name

from django.template import RequestContext
from django.template.backends.django import DjangoTemplates
from django.template.library import InvalidTemplateLibrary
from django.test import RequestFactory, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango110Warning

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

        # Check that context processors run
        content = template.render({}, request)
        self.assertEqual(content, 'yes')

        # Check that context overrides context processors
        content = template.render({'processors': 'no'}, request)
        self.assertEqual(content, 'no')

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_request_context_conflicts_with_request(self):
        template = self.engine.from_string('hello')

        request = RequestFactory().get('/')
        request_context = RequestContext(request)
        # This doesn't raise an exception.
        template.render(request_context, request)

        other_request = RequestFactory().get('/')
        msg = ("render() was called with a RequestContext and a request "
               "argument which refer to different requests. Make sure "
               "that the context argument is a dict or at least that "
               "the two arguments refer to the same request.")
        with self.assertRaisesMessage(ValueError, msg):
            template.render(request_context, other_request)

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
