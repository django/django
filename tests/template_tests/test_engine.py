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

    def test_autoescape_off(self):
        """
        The Engine.render_to_string() method should honor the autoescape
        attribute of the engine.
        """
        engine_with_autoescape_off = Engine(
            dirs=[TEMPLATE_DIR],
            autoescape=False,
        )
        # Create a simple template string with HTML that would normally be escaped
        template_content = '{{ var }}'

        # Save a template file for this test
        template_name = 'test_autoescape.html'
        template_path = os.path.join(TEMPLATE_DIR, template_name)

        try:
            with open(template_path, 'w') as f:
                f.write(template_content)

            # Test with autoescape=False - HTML should NOT be escaped
            output = engine_with_autoescape_off.render_to_string(
                template_name,
                {'var': '<b>test</b>'}
            )
            self.assertEqual(output, '<b>test</b>')

            # Test with default autoescape=True - HTML should be escaped
            output_escaped = self.engine.render_to_string(
                template_name,
                {'var': '<b>test</b>'}
            )
            self.assertEqual(output_escaped, '&lt;b&gt;test&lt;/b&gt;')
        finally:
            # Clean up the test template file
            if os.path.exists(template_path):
                os.remove(template_path)


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
        'OPTIONS': {'file_charset': 'abc'},
    }, {
        'NAME': 'other',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {'file_charset': 'def'},
    }])
    def test_multiple_engines_configured(self):
        self.assertEqual(Engine.get_default().file_charset, 'abc')


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
