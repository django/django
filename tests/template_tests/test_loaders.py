"""
Test cases for the template loaders

Note: This test requires setuptools!
"""

from django.conf import settings

if __name__ == '__main__':
    settings.configure()

import imp
import os.path
import sys
import unittest

try:
    import pkg_resources
except ImportError:
    pkg_resources = None


from django.template import TemplateDoesNotExist, Context
from django.template.loaders.eggs import Loader as EggLoader
from django.template import loader
from django.utils import six
from django.utils._os import upath
from django.utils.six import StringIO


# Mock classes and objects for pkg_resources functions.
class MockLoader(object):
    pass

def create_egg(name, resources):
    """
    Creates a mock egg with a list of resources.

    name: The name of the module.
    resources: A dictionary of resources. Keys are the names and values the data.
    """
    egg = imp.new_module(name)
    egg.__loader__ = MockLoader()
    egg._resources = resources
    sys.modules[name] = egg


@unittest.skipUnless(pkg_resources, 'setuptools is not installed')
class EggLoaderTest(unittest.TestCase):
    def setUp(self):
        # Defined here b/c at module scope we may not have pkg_resources
        class MockProvider(pkg_resources.NullProvider):
            def __init__(self, module):
                pkg_resources.NullProvider.__init__(self, module)
                self.module = module

            def _has(self, path):
                return path in self.module._resources

            def _isdir(self, path):
                return False

            def get_resource_stream(self, manager, resource_name):
                return self.module._resources[resource_name]

            def _get(self, path):
                return self.module._resources[path].read()

        pkg_resources._provider_factories[MockLoader] = MockProvider

        self.empty_egg = create_egg("egg_empty", {})
        self.egg_1 = create_egg("egg_1", {
            os.path.normcase('templates/y.html'): StringIO("y"),
            os.path.normcase('templates/x.txt'): StringIO("x"),
        })
        self._old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = []

    def tearDown(self):
        settings.INSTALLED_APPS = self._old_installed_apps

    def test_empty(self):
        "Loading any template on an empty egg should fail"
        settings.INSTALLED_APPS = ['egg_empty']
        egg_loader = EggLoader()
        self.assertRaises(TemplateDoesNotExist, egg_loader.load_template_source, "not-existing.html")

    def test_non_existing(self):
        "Template loading fails if the template is not in the egg"
        settings.INSTALLED_APPS = ['egg_1']
        egg_loader = EggLoader()
        self.assertRaises(TemplateDoesNotExist, egg_loader.load_template_source, "not-existing.html")

    def test_existing(self):
        "A template can be loaded from an egg"
        settings.INSTALLED_APPS = ['egg_1']
        egg_loader = EggLoader()
        contents, template_name = egg_loader.load_template_source("y.html")
        self.assertEqual(contents, "y")
        self.assertEqual(template_name, "egg:egg_1:templates/y.html")

    def test_not_installed(self):
        "Loading an existent template from an egg not included in INSTALLED_APPS should fail"
        settings.INSTALLED_APPS = []
        egg_loader = EggLoader()
        self.assertRaises(TemplateDoesNotExist, egg_loader.load_template_source, "y.html")


class CachedLoader(unittest.TestCase):
    def setUp(self):
        self.old_TEMPLATE_LOADERS = settings.TEMPLATE_LOADERS
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
            )
            ),
        )
    def tearDown(self):
        settings.TEMPLATE_LOADERS = self.old_TEMPLATE_LOADERS

    def test_templatedir_caching(self):
        "Check that the template directories form part of the template cache key. Refs #13573"
        # Retrive a template specifying a template directory to check
        t1, name = loader.find_template('test.html', (os.path.join(os.path.dirname(upath(__file__)), 'templates', 'first'),))
        # Now retrieve the same template name, but from a different directory
        t2, name = loader.find_template('test.html', (os.path.join(os.path.dirname(upath(__file__)), 'templates', 'second'),))

        # The two templates should not have the same content
        self.assertNotEqual(t1.render(Context({})), t2.render(Context({})))

    def test_missing_template_is_cached(self):
        "#19949 -- Check that the missing template is cached."
        template_loader = loader.find_template_loader(settings.TEMPLATE_LOADERS[0])
        # Empty cache, which may be filled from previous tests.
        template_loader.reset()
        # Check that 'missing.html' isn't already in cache before 'missing.html' is loaded
        self.assertRaises(KeyError, lambda: template_loader.template_cache["missing.html"])
        # Try to load it, it should fail
        self.assertRaises(TemplateDoesNotExist, template_loader.load_template, "missing.html")
        # Verify that the fact that the missing template, which hasn't been found, has actually
        # been cached:
        self.assertEqual(template_loader.template_cache.get("missing.html"),
                         TemplateDoesNotExist,
                         "Cached template loader doesn't cache file lookup misses. It should.")


class RenderToStringTest(unittest.TestCase):

    def setUp(self):
        self._old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(upath(__file__)), 'templates'),
        )

    def tearDown(self):
        settings.TEMPLATE_DIRS = self._old_TEMPLATE_DIRS

    def test_basic(self):
        self.assertEqual(loader.render_to_string('test_context.html'), 'obj:')

    def test_basic_context(self):
        self.assertEqual(loader.render_to_string('test_context.html',
                                                 {'obj': 'test'}), 'obj:test')

    def test_existing_context_kept_clean(self):
        context = Context({'obj': 'before'})
        output = loader.render_to_string('test_context.html', {'obj': 'after'},
                                         context_instance=context)
        self.assertEqual(output, 'obj:after')
        self.assertEqual(context['obj'], 'before')

    def test_empty_list(self):
        six.assertRaisesRegex(self, TemplateDoesNotExist,
                                'No template names provided$',
                                loader.render_to_string, [])

    def test_select_templates_from_empty_list(self):
        six.assertRaisesRegex(self, TemplateDoesNotExist,
                                'No template names provided$',
                                loader.select_template, [])


class TemplateDirsOverrideTest(unittest.TestCase):

    dirs_tuple = (os.path.join(os.path.dirname(upath(__file__)), 'other_templates'),)
    dirs_list = list(dirs_tuple)
    dirs_iter = (dirs_tuple, dirs_list)

    def test_render_to_string(self):
        for dirs in self.dirs_iter:
            self.assertEqual(loader.render_to_string('test_dirs.html', dirs=dirs), 'spam eggs\n')

    def test_get_template(self):
        for dirs in self.dirs_iter:
            template = loader.get_template('test_dirs.html', dirs=dirs)
            self.assertEqual(template.render(Context({})), 'spam eggs\n')

    def test_select_template(self):
        for dirs in self.dirs_iter:
            template = loader.select_template(['test_dirs.html'], dirs=dirs)
            self.assertEqual(template.render(Context({})), 'spam eggs\n')
