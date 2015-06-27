import os

from django.template import Context
from django.template.engine import Engine
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning

from .utils import ROOT, TEMPLATE_DIR

OTHER_DIR = os.path.join(ROOT, 'other_templates')


@ignore_warnings(category=RemovedInDjango110Warning)
class DeprecatedRenderToStringTest(SimpleTestCase):

    def setUp(self):
        self.engine = Engine(
            dirs=[TEMPLATE_DIR],
            libraries={'custom': 'template_tests.templatetags.custom'},
        )

    def test_basic_context(self):
        self.assertEqual(
            self.engine.render_to_string('test_context.html', {'obj': 'test'}),
            'obj:test\n',
        )

    def test_existing_context_kept_clean(self):
        context = Context({'obj': 'before'})
        output = self.engine.render_to_string(
            'test_context.html', {'obj': 'after'}, context_instance=context,
        )
        self.assertEqual(output, 'obj:after\n')
        self.assertEqual(context['obj'], 'before')

    def test_no_empty_dict_pushed_to_stack(self):
        """
        #21741 -- An empty dict should not be pushed to the context stack when
        render_to_string is called without a context argument.
        """

        # The stack should have a length of 1, corresponding to the builtins
        self.assertEqual(
            '1',
            self.engine.render_to_string('test_context_stack.html').strip(),
        )
        self.assertEqual(
            '1',
            self.engine.render_to_string(
                'test_context_stack.html',
                context_instance=Context()
            ).strip(),
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


@ignore_warnings(category=RemovedInDjango110Warning)
class TemplateDirsOverrideTests(SimpleTestCase):
    DIRS = ((OTHER_DIR, ), [OTHER_DIR])

    def setUp(self):
        self.engine = Engine()

    def test_render_to_string(self):
        for dirs in self.DIRS:
            self.assertEqual(
                self.engine.render_to_string('test_dirs.html', dirs=dirs),
                'spam eggs\n',
            )

    def test_get_template(self):
        for dirs in self.DIRS:
            template = self.engine.get_template('test_dirs.html', dirs=dirs)
            self.assertEqual(template.render(Context()), 'spam eggs\n')

    def test_select_template(self):
        for dirs in self.DIRS:
            template = self.engine.select_template(['test_dirs.html'], dirs=dirs)
            self.assertEqual(template.render(Context()), 'spam eggs\n')
