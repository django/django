from pathlib import Path
from unittest import skipIf

from django.template import TemplateSyntaxError
from django.test import RequestFactory

from .test_dummy import TemplateStringsTests

try:
    import jinja2
except ImportError:
    jinja2 = None
    Jinja2 = None
else:
    from django.template.backends.jinja2 import Jinja2


@skipIf(jinja2 is None, "this test requires jinja2")
class Jinja2Tests(TemplateStringsTests):

    engine_class = Jinja2
    backend_name = 'jinja2'
    options = {
        'keep_trailing_newline': True,
        'context_processors': [
            'django.template.context_processors.static',
        ],
    }

    def test_origin(self):
        template = self.engine.get_template('template_backends/hello.html')
        self.assertTrue(template.origin.name.endswith('hello.html'))
        self.assertEqual(template.origin.template_name, 'template_backends/hello.html')

    def test_origin_from_string(self):
        template = self.engine.from_string('Hello!\n')
        self.assertEqual(template.origin.name, '<template>')
        self.assertIsNone(template.origin.template_name)

    def test_self_context(self):
        """
        Using 'self' in the context should not throw errors (#24538).
        """
        # self will be overridden to be a TemplateReference, so the self
        # variable will not come through. Attempting to use one though should
        # not throw an error.
        template = self.engine.from_string('hello {{ foo }}!')
        content = template.render(context={'self': 'self', 'foo': 'world'})
        self.assertEqual(content, 'hello world!')

    def test_exception_debug_info_min_context(self):
        with self.assertRaises(TemplateSyntaxError) as e:
            self.engine.get_template('template_backends/syntax_error.html')
        debug = e.exception.template_debug
        self.assertEqual(debug['after'], '')
        self.assertEqual(debug['before'], '')
        self.assertEqual(debug['during'], '{% block %}')
        self.assertEqual(debug['bottom'], 1)
        self.assertEqual(debug['top'], 0)
        self.assertEqual(debug['line'], 1)
        self.assertEqual(debug['total'], 1)
        self.assertEqual(len(debug['source_lines']), 1)
        self.assertTrue(debug['name'].endswith('syntax_error.html'))
        self.assertIn('message', debug)

    def test_exception_debug_info_max_context(self):
        with self.assertRaises(TemplateSyntaxError) as e:
            self.engine.get_template('template_backends/syntax_error2.html')
        debug = e.exception.template_debug
        self.assertEqual(debug['after'], '')
        self.assertEqual(debug['before'], '')
        self.assertEqual(debug['during'], '{% block %}')
        self.assertEqual(debug['bottom'], 26)
        self.assertEqual(debug['top'], 5)
        self.assertEqual(debug['line'], 16)
        self.assertEqual(debug['total'], 31)
        self.assertEqual(len(debug['source_lines']), 21)
        self.assertTrue(debug['name'].endswith('syntax_error2.html'))
        self.assertIn('message', debug)

    def test_context_processors(self):
        request = RequestFactory().get('/')
        template = self.engine.from_string('Static URL: {{ STATIC_URL }}')
        content = template.render(request=request)
        self.assertEqual(content, 'Static URL: /static/')
        with self.settings(STATIC_URL='/s/'):
            content = template.render(request=request)
        self.assertEqual(content, 'Static URL: /s/')

    def test_dirs_pathlib(self):
        engine = Jinja2({
            'DIRS': [Path(__file__).parent / 'templates' / 'template_backends'],
            'APP_DIRS': False,
            'NAME': 'jinja2',
            'OPTIONS': {},
        })
        template = engine.get_template('hello.html')
        self.assertEqual(template.render({'name': 'Joe'}), 'Hello Joe!')
