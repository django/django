"""
Test cases for the template loaders

Note: This test requires setuptools!
"""

from django.conf import settings

if __name__ == '__main__':
    settings.configure()

import unittest
import sys
import pkg_resources
import imp
import StringIO
import os.path

from django.template import TemplateDoesNotExist
from django.template.loaders.eggs import load_template_source as lts_egg

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
    resources: A dictionary of resources. Keys are the names and values the the data.
    """
    egg = imp.new_module(name)
    egg.__loader__ = MockLoader()
    egg._resources = resources
    sys.modules[name] = egg

class EggLoader(unittest.TestCase):
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
        self.assertRaises(TemplateDoesNotExist, lts_egg, "not-existing.html")

    def test_non_existing(self):
        "Template loading fails if the template is not in the egg"
        settings.INSTALLED_APPS = ['egg_1']
        self.assertRaises(TemplateDoesNotExist, lts_egg, "not-existing.html")

    def test_existing(self):
        "A template can be loaded from an egg"
        settings.INSTALLED_APPS = ['egg_1']
        contents, template_name = lts_egg("y.html")
        self.assertEqual(contents, "y")
        self.assertEqual(template_name, "egg:egg_1:templates/y.html")

    def test_not_installed(self):
        "Loading an existent template from an egg not included in INSTALLED_APPS should fail"
        settings.INSTALLED_APPS = []
        self.assertRaises(TemplateDoesNotExist, lts_egg, "y.html")

if __name__ == "__main__":
    unittest.main()
