import os
import sys
import imp
from zipimport import zipimporter

from django.core.exceptions import ImproperlyConfigured
from django.utils import unittest
from django.utils.importlib import import_module
from django.utils.module_loading import import_by_path, module_has_submodule
from django.utils._os import upath


class DefaultLoader(unittest.TestCase):
    def setUp(self):
        sys.meta_path.insert(0, ProxyFinder())

    def tearDown(self):
        sys.meta_path.pop(0)

    def test_loader(self):
        "Normal module existence can be tested"
        test_module = import_module('regressiontests.utils.test_module')
        test_no_submodule = import_module(
            'regressiontests.utils.test_no_submodule')

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

        # A child that doesn't exist, but is the name of a package on the path
        self.assertFalse(module_has_submodule(test_module, 'django'))
        self.assertRaises(ImportError, import_module, 'regressiontests.utils.test_module.django')

        # Don't be confused by caching of import misses
        import types  # causes attempted import of regressiontests.utils.types
        self.assertFalse(module_has_submodule(sys.modules['regressiontests.utils'], 'types'))

        # A module which doesn't have a __path__ (so no submodules)
        self.assertFalse(module_has_submodule(test_no_submodule, 'anything'))
        self.assertRaises(ImportError, import_module,
            'regressiontests.utils.test_no_submodule.anything')

class EggLoader(unittest.TestCase):
    def setUp(self):
        self.old_path = sys.path[:]
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

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


class ModuleImportTestCase(unittest.TestCase):
    def test_import_by_path(self):
        cls = import_by_path(
            'django.utils.module_loading.import_by_path')
        self.assertEqual(cls, import_by_path)

        # Test exceptions raised
        for path in ('no_dots_in_path', 'unexistent.path',
                'tests.regressiontests.utils.unexistent'):
            self.assertRaises(ImproperlyConfigured, import_by_path, path)

        with self.assertRaises(ImproperlyConfigured) as cm:
            import_by_path('unexistent.module.path', error_prefix="Foo")
        self.assertTrue(str(cm.exception).startswith('Foo'))


class ProxyFinder(object):
    def __init__(self):
        self._cache = {}

    def find_module(self, fullname, path=None):
        tail = fullname.rsplit('.', 1)[-1]
        try:
            fd, fn, info = imp.find_module(tail, path)
            if fullname in self._cache:
                old_fd = self._cache[fullname][0]
                if old_fd:
                    old_fd.close()
            self._cache[fullname] = (fd, fn, info)
        except ImportError:
            return None
        else:
            return self  # this is a loader as well

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        fd, fn, info = self._cache[fullname]
        try:
            return imp.load_module(fullname, fd, fn, info)
        finally:
            if fd:
                fd.close()

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
