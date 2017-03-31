import os

from django.core.exceptions import ImproperlyConfigured
from django.template import Context
from django.template.engine import Engine
from django.test import SimpleTestCase, override_settings

from .utils import ROOT, TEMPLATE_DIR

OTHER_DIR = os.path.join(ROOT, 'other_templates')


class RenderToStringTest(SimpleTestCase):

    def setUp(self):
        self.engine = Engine(dirs=[TEMPLATE_DIR])

    def test_basic_context(self):
        self.assertEqual(
            self.engine.render_to_string('test_context.html', {'obj': 'test'}),
            'obj:test\n',
        )


class GetDefaultTests(SimpleTestCase):

    @override_settings(TEMPLATES=[])
    def test_no_engines_configured(self):
        msg = 'No DjangoTemplates backend is configured.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            Engine.get_default()

    @override_settings(TEMPLATES=[{
        'NAME': 'default',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {'file_charset': 'abc'},
    }])
    def test_single_engine_configured(self):
        self.assertEqual(Engine.get_default().file_charset, 'abc')

    @override_settings(TEMPLATES=[{
        'NAME': 'default',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }, {
        'NAME': 'other',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }])
    def test_multiple_engines_configured(self):
        msg = 'Several DjangoTemplates backends are configured. You must select one explicitly.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            Engine.get_default()


class LoaderTests(SimpleTestCase):

    def test_origin(self):
        engine = Engine(dirs=[TEMPLATE_DIR], debug=True)
        template = engine.get_template('index.html')
        self.assertEqual(template.origin.template_name, 'index.html')

    def test_loader_priority(self):
        """
        #21460 -- The order of template loader works.
        """
        loaders = [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]
        engine = Engine(dirs=[OTHER_DIR, TEMPLATE_DIR], loaders=loaders)
        template = engine.get_template('priority/foo.html')
        self.assertEqual(template.render(Context()), 'priority\n')

    def test_cached_loader_priority(self):
        """
        The order of template loader works. Refs #21460.
        """
        loaders = [
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]),
        ]
        engine = Engine(dirs=[OTHER_DIR, TEMPLATE_DIR], loaders=loaders)

        template = engine.get_template('priority/foo.html')
        self.assertEqual(template.render(Context()), 'priority\n')

        template = engine.get_template('priority/foo.html')
        self.assertEqual(template.render(Context()), 'priority\n')
