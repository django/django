"""
Test cases for the template loaders

Note: This test requires setuptools!
"""

from django.conf import settings

if __name__ == '__main__':
    settings.configure()

import sys
import pkg_resources
import imp
import StringIO
import os.path
import warnings

from django.template import TemplateDoesNotExist, Context
from django.template.loaders.eggs import load_template_source as lts_egg
from django.template.loaders.eggs import Loader as EggLoader
from django.template import loader
from django.utils import unittest


# Mock classes and objects for pkg_resources functions.
class MockProvider(pkg_resources.NullProvider):
    def __init__(self, module):
        pkg_resources.NullProvider.__init__(self, module)
        self.module = module

    def _has(self, path):
        return path in self.module._resources

    def _isdir(self,path):
        return False

    def get_resource_stream(self, manager, resource_name):
        return self.module._resources[resource_name]

    def _get(self, path):
        return self.module._resources[path].read()

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

class DeprecatedEggLoaderTest(unittest.TestCase):
    "Test the deprecated load_template_source interface to the egg loader"
    def setUp(self):
        pkg_resources._provider_factories[MockLoader] = MockProvider

        self.empty_egg = create_egg("egg_empty", {})
        self.egg_1 = create_egg("egg_1", {
            os.path.normcase('templates/y.html') : StringIO.StringIO("y"),
            os.path.normcase('templates/x.txt') : StringIO.StringIO("x"),
        })
        self._old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = []
        warnings.filterwarnings("ignore", category=DeprecationWarning,
                                module='django.template.loaders.eggs')

    def tearDown(self):
        settings.INSTALLED_APPS = self._old_installed_apps
        warnings.resetwarnings()
        warnings.simplefilter("ignore", PendingDeprecationWarning)

    def test_existing(self):
        "A template can be loaded from an egg"
        settings.INSTALLED_APPS = ['egg_1']
        contents, template_name = lts_egg("y.html")
        self.assertEqual(contents, "y")
        self.assertEqual(template_name, "egg:egg_1:templates/y.html")


class EggLoaderTest(unittest.TestCase):
    def setUp(self):
        pkg_resources._provider_factories[MockLoader] = MockProvider

        self.empty_egg = create_egg("egg_empty", {})
        self.egg_1 = create_egg("egg_1", {
            os.path.normcase('templates/y.html') : StringIO.StringIO("y"),
            os.path.normcase('templates/x.txt') : StringIO.StringIO("x"),
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
        t1, name = loader.find_template('test.html', (os.path.join(os.path.dirname(__file__), 'templates', 'first'),))
        # Now retrieve the same template name, but from a different directory
        t2, name = loader.find_template('test.html', (os.path.join(os.path.dirname(__file__), 'templates', 'second'),))

        # The two templates should not have the same content
        self.assertNotEqual(t1.render(Context({})), t2.render(Context({})))

if __name__ == "__main__":
    unittest.main()
