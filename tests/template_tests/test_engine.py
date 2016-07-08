import os

from django.template import Context
from django.template.engine import Engine
from django.test import SimpleTestCase

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


class LoaderTests(SimpleTestCase):

    def test_origin(self):
        engine = Engine(dirs=[TEMPLATE_DIR], debug=True)
        template = engine.get_template('index.html')
        self.assertEqual(template.origin.template_name, 'index.html')

    def test_loader_priority(self):
        """
        #21460 -- Check that the order of template loader works.
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
        Check that the order of template loader works. Refs #21460.
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
