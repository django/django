import os

from django.template import Context, Engine, TemplateDoesNotExist
from django.template.loader_tags import ExtendsError
from django.template.loaders.base import Loader
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango20Warning

from .utils import ROOT

RECURSIVE = os.path.join(ROOT, 'recursive_templates')


class ExtendsBehaviorTests(SimpleTestCase):

    def test_normal_extend(self):
        engine = Engine(dirs=[os.path.join(RECURSIVE, 'fs')])
        template = engine.get_template('one.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three two one')

    def test_extend_recursive(self):
        engine = Engine(dirs=[
            os.path.join(RECURSIVE, 'fs'),
            os.path.join(RECURSIVE, 'fs2'),
            os.path.join(RECURSIVE, 'fs3'),
        ])
        template = engine.get_template('recursive.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'fs3/recursive fs2/recursive fs/recursive')

    def test_extend_missing(self):
        engine = Engine(dirs=[os.path.join(RECURSIVE, 'fs')])
        template = engine.get_template('extend-missing.html')
        with self.assertRaises(TemplateDoesNotExist) as e:
            template.render(Context({}))

        tried = e.exception.tried
        self.assertEqual(len(tried), 1)
        self.assertEqual(tried[0][0].template_name, 'missing.html')

    def test_recursive_multiple_loaders(self):
        engine = Engine(
            dirs=[os.path.join(RECURSIVE, 'fs')],
            loaders=[(
                'django.template.loaders.locmem.Loader', {
                    'one.html': (
                        '{% extends "one.html" %}{% block content %}{{ block.super }} locmem-one{% endblock %}'
                    ),
                    'two.html': (
                        '{% extends "two.html" %}{% block content %}{{ block.super }} locmem-two{% endblock %}'
                    ),
                    'three.html': (
                        '{% extends "three.html" %}{% block content %}{{ block.super }} locmem-three{% endblock %}'
                    ),
                }
            ), 'django.template.loaders.filesystem.Loader'],
        )
        template = engine.get_template('one.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'three locmem-three two locmem-two one locmem-one')

    def test_extend_self_error(self):
        """
        Catch if a template extends itself and no other matching
        templates are found.
        """
        engine = Engine(dirs=[os.path.join(RECURSIVE, 'fs')])
        template = engine.get_template('self.html')
        with self.assertRaises(TemplateDoesNotExist):
            template.render(Context({}))

    def test_extend_cached(self):
        engine = Engine(
            dirs=[
                os.path.join(RECURSIVE, 'fs'),
                os.path.join(RECURSIVE, 'fs2'),
                os.path.join(RECURSIVE, 'fs3'),
            ],
            loaders=[
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                ]),
            ],
        )
        template = engine.get_template('recursive.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'fs3/recursive fs2/recursive fs/recursive')

        cache = engine.template_loaders[0].get_template_cache
        self.assertEqual(len(cache), 3)
        expected_path = os.path.join('fs', 'recursive.html')
        self.assertTrue(cache['recursive.html'].origin.name.endswith(expected_path))

        # Render another path that uses the same templates from the cache
        template = engine.get_template('other-recursive.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'fs3/recursive fs2/recursive fs/recursive')

        # Template objects should not be duplicated.
        self.assertEqual(len(cache), 4)
        expected_path = os.path.join('fs', 'other-recursive.html')
        self.assertTrue(cache['other-recursive.html'].origin.name.endswith(expected_path))

    def test_unique_history_per_loader(self):
        """
        Extending should continue even if two loaders return the same
        name for a template.
        """
        engine = Engine(
            loaders=[
                ['django.template.loaders.locmem.Loader', {
                    'base.html': '{% extends "base.html" %}{% block content %}{{ block.super }} loader1{% endblock %}',
                }],
                ['django.template.loaders.locmem.Loader', {
                    'base.html': '{% block content %}loader2{% endblock %}',
                }],
            ]
        )
        template = engine.get_template('base.html')
        output = template.render(Context({}))
        self.assertEqual(output.strip(), 'loader2 loader1')


class NonRecursiveLoader(Loader):

    def __init__(self, engine, templates_dict):
        self.templates_dict = templates_dict
        super(NonRecursiveLoader, self).__init__(engine)

    def load_template_source(self, template_name, template_dirs=None):
        try:
            return self.templates_dict[template_name], template_name
        except KeyError:
            raise TemplateDoesNotExist(template_name)


@ignore_warnings(category=RemovedInDjango20Warning)
class NonRecursiveLoaderExtendsTests(SimpleTestCase):

    loaders = [
        ('template_tests.test_extends.NonRecursiveLoader', {
            'base.html': 'base',
            'index.html': '{% extends "base.html" %}',
            'recursive.html': '{% extends "recursive.html" %}',
            'other-recursive.html': '{% extends "recursive.html" %}',
            'a.html': '{% extends "b.html" %}',
            'b.html': '{% extends "a.html" %}',
        }),
    ]

    def test_extend(self):
        engine = Engine(loaders=self.loaders)
        output = engine.render_to_string('index.html')
        self.assertEqual(output, 'base')

    def test_extend_cached(self):
        engine = Engine(loaders=[
            ('django.template.loaders.cached.Loader', self.loaders),
        ])
        output = engine.render_to_string('index.html')
        self.assertEqual(output, 'base')

        cache = engine.template_loaders[0].template_cache
        self.assertIn('base.html', cache)
        self.assertIn('index.html', cache)

        # Render a second time from cache
        output = engine.render_to_string('index.html')
        self.assertEqual(output, 'base')

    def test_extend_error(self):
        engine = Engine(loaders=self.loaders)
        msg = 'Cannot extend templates recursively when using non-recursive template loaders'

        with self.assertRaisesMessage(ExtendsError, msg):
            engine.render_to_string('recursive.html')

        with self.assertRaisesMessage(ExtendsError, msg):
            engine.render_to_string('other-recursive.html')

        with self.assertRaisesMessage(ExtendsError, msg):
            engine.render_to_string('a.html')
