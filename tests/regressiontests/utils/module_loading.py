import os
import sys
from unittest import TestCase
from zipimport import zipimporter

from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

class DefaultLoader(TestCase):
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

class EggLoader(TestCase):
    def setUp(self):
        self.old_path = sys.path
        self.egg_dir = '%s/eggs' % os.path.dirname(__file__)

    def tearDown(self):
        sys.path = self.old_path

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

class CustomLoader(TestCase):
    def setUp(self):
        self.egg_dir = '%s/eggs' % os.path.dirname(__file__)
        self.old_path = sys.path
        sys.path_hooks.insert(0, TestFinder)
        sys.path_importer_cache.clear()

    def tearDown(self):
        sys.path = self.old_path
        sys.path_hooks.pop(0)

    def test_shallow_loader(self):
        "Module existence can be tested with a custom loader"
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
        "Modules existence can be tested deep inside a custom loader"
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
