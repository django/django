from django.forms.renderers.templates import TemplateRenderer
from django.template.backends.django import DjangoTemplates
from django.template.backends.jinja2 import Jinja2
from django.template.loader import get_template
from django.test import SimpleTestCase, override_settings


class RendererTest(SimpleTestCase):

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.dummy.TemplateStrings',
    }])
    def test_default_instantiation(self):
        renderer = TemplateRenderer()
        engine = renderer.engine
        self.assertTrue(isinstance(engine, Jinja2))
        self.assertEqual(renderer.loader, engine.get_template)

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'NAME': 'override',
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.locmem.Loader', {
                    'text.html': 'text',
                }),
            ],
        },
    }])
    def test_engine_name(self):
        class CustomRenderer(TemplateRenderer):
            engine_name = 'override'

        renderer = CustomRenderer()
        self.assertTrue(isinstance(renderer.engine, DjangoTemplates))
        self.assertEqual(renderer.loader, renderer.engine.get_template)
        self.assertEqual(renderer.render('text.html', {}), 'text')

    @override_settings(
        INSTALLED_APPS=['django.forms'],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'APP_DIRS': True,
        }],
    )
    def test_engine_from_settings(self):
        renderer = TemplateRenderer()
        self.assertEqual(renderer.engine, None)
        self.assertEqual(renderer.loader, get_template)

    @override_settings(
        INSTALLED_APPS=['django.forms'],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {
                'loaders': [
                    'django.template.loaders.app_directories.Loader',
                ],
            },
        }],
    )
    def test_with_app_loader(self):
        renderer = TemplateRenderer()
        self.assertEqual(renderer.engine, None)
        self.assertEqual(renderer.loader, get_template)
