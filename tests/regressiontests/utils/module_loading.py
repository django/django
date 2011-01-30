import os
import sys
from zipimport import zipimporter

from django.utils import unittest
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule


class DefaultLoader(unittest.TestCase):
    def test_loader(self):
        "Normal module existence can be tested"
        test_module = import_module('regressiontests.utils.test_module')

        # An importable child
        self.assertTrue(module_has_submodule(test_module, 'good_module'))
        mod = import_module('regressiontests.utils.test_module.good_module')
        self.assertEqual(mod.content, 'Good Module')

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(test_module, 'bad_module'))
        self.assertRaises(ImportError, import_module, 'regressiontests.utils.test_module.bad_module')

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(test_module, 'no_such_module'))
        self.assertRaises(ImportError, import_module, 'regressiontests.utils.test_module.no_such_module')

        # Don't be confused by caching of import misses
        import types  # causes attempted import of regressiontests.utils.types
        self.assertFalse(module_has_submodule(sys.modules['regressiontests.utils'], 'types'))

class EggLoader(unittest.TestCase):
    def setUp(self):
        self.old_path = sys.path[:]
        self.egg_dir = '%s/eggs' % os.path.dirname(__file__)

    def tearDown(self):
        sys.path = self.old_path
        sys.path_importer_cache.clear()

        sys.modules.pop('egg_module.sub1.sub2.bad_module', None)
        sys.modules.pop('egg_module.sub1.sub2.good_module', None)
        sys.modules.pop('egg_module.sub1.sub2', None)
        sys.modules.pop('egg_module.sub1', None)
        sys.modules.pop('egg_module.bad_module', None)
        sys.modules.pop('egg_module.good_module', None)
        sys.modules.pop('egg_module', None)

    def test_shallow_loader(self):
        "Module existence can be tested inside eggs"
        egg_name = '%s/test_egg.egg' % self.egg_dir
        sys.path.append(egg_name)
        egg_module = import_module('egg_module')

        # An importable child
        self.assertTrue(module_has_submodule(egg_module, 'good_module'))
        mod = import_module('egg_module.good_module')
        self.assertEqual(mod.content, 'Good Module')

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(egg_module, 'bad_module'))
        self.assertRaises(ImportError, import_module, 'egg_module.bad_module')

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(egg_module, 'no_such_module'))
        self.assertRaises(ImportError, import_module, 'egg_module.no_such_module')

    def test_deep_loader(self):
        "Modules deep inside an egg can still be tested for existence"
        egg_name = '%s/test_egg.egg' % self.egg_dir
        sys.path.append(egg_name)
        egg_module = import_module('egg_module.sub1.sub2')

        # An importable child
        self.assertTrue(module_has_submodule(egg_module, 'good_module'))
        mod = import_module('egg_module.sub1.sub2.good_module')
        self.assertEqual(mod.content, 'Deep Good Module')

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(egg_module, 'bad_module'))
        self.assertRaises(ImportError, import_module, 'egg_module.sub1.sub2.bad_module')

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(egg_module, 'no_such_module'))
        self.assertRaises(ImportError, import_module, 'egg_module.sub1.sub2.no_such_module')

class TestFinder(object):
    def __init__(self, *args, **kwargs):
        self.importer = zipimporter(*args, **kwargs)

    def find_module(self, path):
        importer = self.importer.find_module(path)
        if importer is None:
            return
        return TestLoader(importer)

class TestLoader(object):
    def __init__(self, importer):
        self.importer = importer

    def load_module(self, name):
        mod = self.importer.load_module(name)
        mod.__loader__ = self
        return mod

class CustomLoader(EggLoader):
    """The Custom Loader test is exactly the same as the EggLoader, but
    it uses a custom defined Loader and Finder that is intentionally
    split into two classes. Although the EggLoader combines both functions
    into one class, this isn't required.
    """
    def setUp(self):
        super(CustomLoader, self).setUp()
        sys.path_hooks.insert(0, TestFinder)
        sys.path_importer_cache.clear()

    def tearDown(self):
        super(CustomLoader, self).tearDown()
        sys.path_hooks.pop(0)
