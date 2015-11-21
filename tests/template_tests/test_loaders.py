# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager

from django.template import Context, TemplateDoesNotExist
from django.template.engine import Engine
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning

from .utils import ROOT, TEMPLATE_DIR

try:
    import pkg_resources
except ImportError:
    pkg_resources = None

OTHER_DIR = os.path.join(ROOT, 'other_templates')


class CachedLoaderTests(SimpleTestCase):

    def setUp(self):
        self.engine = Engine(
            dirs=[TEMPLATE_DIR],
            loaders=[
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                ]),
            ],
        )

    def test_get_template(self):
        template = self.engine.get_template('index.html')
        self.assertEqual(template.origin.name, os.path.join(TEMPLATE_DIR, 'index.html'))
        self.assertEqual(template.origin.template_name, 'index.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0].loaders[0])

        cache = self.engine.template_loaders[0].get_template_cache
        self.assertEqual(cache['index.html'], template)

        # Run a second time from cache
        template = self.engine.get_template('index.html')
        self.assertEqual(template.origin.name, os.path.join(TEMPLATE_DIR, 'index.html'))
        self.assertEqual(template.origin.template_name, 'index.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0].loaders[0])

    def test_get_template_missing(self):
        with self.assertRaises(TemplateDoesNotExist):
            self.engine.get_template('doesnotexist.html')
        e = self.engine.template_loaders[0].get_template_cache['doesnotexist.html']
        self.assertEqual(e.args[0], 'doesnotexist.html')

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_load_template(self):
        loader = self.engine.template_loaders[0]
        template, origin = loader.load_template('index.html')
        self.assertEqual(template.origin.template_name, 'index.html')

        cache = self.engine.template_loaders[0].template_cache
        self.assertEqual(cache['index.html'][0], template)

        # Run a second time from cache
        loader = self.engine.template_loaders[0]
        source, name = loader.load_template('index.html')
        self.assertEqual(template.origin.template_name, 'index.html')

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_load_template_missing(self):
        """
        #19949 -- TemplateDoesNotExist exceptions should be cached.
        """
        loader = self.engine.template_loaders[0]

        self.assertFalse('missing.html' in loader.template_cache)

        with self.assertRaises(TemplateDoesNotExist):
            loader.load_template("missing.html")

        self.assertEqual(
            loader.template_cache["missing.html"],
            TemplateDoesNotExist,
            "Cached loader failed to cache the TemplateDoesNotExist exception",
        )

    def test_templatedir_caching(self):
        """
        #13573 -- Template directories should be part of the cache key.
        """
        # Retrieve a template specifying a template directory to check
        t1, name = self.engine.find_template('test.html', (os.path.join(TEMPLATE_DIR, 'first'),))
        # Now retrieve the same template name, but from a different directory
        t2, name = self.engine.find_template('test.html', (os.path.join(TEMPLATE_DIR, 'second'),))

        # The two templates should not have the same content
        self.assertNotEqual(t1.render(Context({})), t2.render(Context({})))

    def test_auto_reload_disabled(self):
        loader = self.engine.template_loaders[0]
        self.assertFalse(loader.auto_reload)


class CachedAutoReloaderTests(SimpleTestCase):

    def setUp(self):
        self.engine = Engine(
            dirs=[OTHER_DIR, TEMPLATE_DIR],
            auto_reload=True,
            loaders=[
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                ]),
            ],
        )

    def test_auto_reload_enabled(self):
        loader = self.engine.template_loaders[0]
        self.assertTrue(loader.auto_reload)

    def test_auto_reload_caches(self):
        template1 = self.engine.get_template('autoreload.html')
        template2 = self.engine.get_template('autoreload.html')
        self.assertIs(template1, template2)

    def test_auto_reload_reloads(self):
        template1 = self.engine.get_template('autoreload.html')
        try:
            self.assertEqual(template1.render(Context()), 'initial\n')
            with open(template1.origin.name, 'w') as f:
                f.write('changed\n')
            template2 = self.engine.get_template('autoreload.html')
            self.assertFalse(template1 is template2)
            self.assertEqual(template2.render(Context()), 'changed\n')
        finally:
            with open(template1.origin.name, 'w') as f:
                f.write('initial\n')

    def test_auto_reload_priority(self):
        priority_path = os.path.join(OTHER_DIR, 'priority', 'autoreload.html')
        try:
            template1 = self.engine.get_template('priority/autoreload.html')
            self.assertEqual(template1.render(Context()), 'no priority\n')
            with open(priority_path, 'w') as f:
                f.write('priority\n')
            template2 = self.engine.get_template('priority/autoreload.html')
            self.assertFalse(template1 is template2)
            self.assertEqual(template2.render(Context()), 'priority\n')
        finally:
            if os.path.exists(priority_path):
                os.remove(priority_path)

    def test_auto_reload_template_does_not_exist(self):
        missing_path = os.path.join(TEMPLATE_DIR, 'does_not_exist.html')
        try:
            self.assertRaises(TemplateDoesNotExist, self.engine.get_template, 'does_not_exist.html')
            open(missing_path, 'w').close()
            try:
                self.engine.get_template('does_not_exist.html')
            except TemplateDoesNotExist:
                self.fail('Expected template to be found')
        finally:
            if os.path.exists(missing_path):
                os.remove(missing_path)





@unittest.skipUnless(pkg_resources, 'setuptools is not installed')
class EggLoaderTests(SimpleTestCase):

    @contextmanager
    def create_egg(self, name, resources):
        """
        Creates a mock egg with a list of resources.

        name: The name of the module.
        resources: A dictionary of template names mapped to file-like objects.
        """

        if six.PY2:
            name = name.encode('utf-8')

        class MockLoader(object):
            pass

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

            def _fn(self, base, resource_name):
                return os.path.normcase(resource_name)

        egg = types.ModuleType(name)
        egg.__loader__ = MockLoader()
        egg.__path__ = ['/some/bogus/path/']
        egg.__file__ = '/some/bogus/path/__init__.pyc'
        egg._resources = resources
        sys.modules[name] = egg
        pkg_resources._provider_factories[MockLoader] = MockProvider

        try:
            yield
        finally:
            del sys.modules[name]
            del pkg_resources._provider_factories[MockLoader]

    @classmethod
    @ignore_warnings(category=RemovedInDjango20Warning)
    def setUpClass(cls):
        cls.engine = Engine(loaders=[
            'django.template.loaders.eggs.Loader',
        ])
        cls.loader = cls.engine.template_loaders[0]
        super(EggLoaderTests, cls).setUpClass()

    def test_get_template(self):
        templates = {
            os.path.normcase('templates/y.html'): six.StringIO("y"),
        }

        with self.create_egg('egg', templates):
            with override_settings(INSTALLED_APPS=['egg']):
                template = self.engine.get_template("y.html")

        self.assertEqual(template.origin.name, 'egg:egg:templates/y.html')
        self.assertEqual(template.origin.template_name, 'y.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0])

        output = template.render(Context({}))
        self.assertEqual(output, "y")

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_load_template_source(self):
        loader = self.engine.template_loaders[0]
        templates = {
            os.path.normcase('templates/y.html'): six.StringIO("y"),
        }

        with self.create_egg('egg', templates):
            with override_settings(INSTALLED_APPS=['egg']):
                source, name = loader.load_template_source('y.html')

        self.assertEqual(source.strip(), 'y')
        self.assertEqual(name, 'egg:egg:templates/y.html')

    def test_non_existing(self):
        """
        Template loading fails if the template is not in the egg.
        """
        with self.create_egg('egg', {}):
            with override_settings(INSTALLED_APPS=['egg']):
                with self.assertRaises(TemplateDoesNotExist):
                    self.engine.get_template('not-existing.html')

    def test_not_installed(self):
        """
        Template loading fails if the egg is not in INSTALLED_APPS.
        """
        templates = {
            os.path.normcase('templates/y.html'): six.StringIO("y"),
        }

        with self.create_egg('egg', templates):
            with self.assertRaises(TemplateDoesNotExist):
                self.engine.get_template('y.html')


class FileSystemLoaderTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(dirs=[TEMPLATE_DIR])
        super(FileSystemLoaderTests, cls).setUpClass()

    @contextmanager
    def set_dirs(self, dirs):
        original_dirs = self.engine.dirs
        self.engine.dirs = dirs
        try:
            yield
        finally:
            self.engine.dirs = original_dirs

    @contextmanager
    def source_checker(self, dirs):
        loader = self.engine.template_loaders[0]

        def check_sources(path, expected_sources):
            expected_sources = [os.path.abspath(s) for s in expected_sources]
            self.assertEqual(
                [origin.name for origin in loader.get_template_sources(path)],
                expected_sources,
            )

        with self.set_dirs(dirs):
            yield check_sources

    def test_get_template(self):
        template = self.engine.get_template('index.html')
        self.assertEqual(template.origin.name, os.path.join(TEMPLATE_DIR, 'index.html'))
        self.assertEqual(template.origin.template_name, 'index.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0])
        self.assertEqual(template.origin.loader_name, 'django.template.loaders.filesystem.Loader')

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_load_template_source(self):
        loader = self.engine.template_loaders[0]
        source, name = loader.load_template_source('index.html')
        self.assertEqual(source.strip(), 'index')
        self.assertEqual(name, os.path.join(TEMPLATE_DIR, 'index.html'))

    def test_directory_security(self):
        with self.source_checker(['/dir1', '/dir2']) as check_sources:
            check_sources('index.html', ['/dir1/index.html', '/dir2/index.html'])
            check_sources('/etc/passwd', [])
            check_sources('etc/passwd', ['/dir1/etc/passwd', '/dir2/etc/passwd'])
            check_sources('../etc/passwd', [])
            check_sources('../../../etc/passwd', [])
            check_sources('/dir1/index.html', ['/dir1/index.html'])
            check_sources('../dir2/index.html', ['/dir2/index.html'])
            check_sources('/dir1blah', [])
            check_sources('../dir1blah', [])

    def test_unicode_template_name(self):
        with self.source_checker(['/dir1', '/dir2']) as check_sources:
            # UTF-8 bytestrings are permitted.
            check_sources(b'\xc3\x85ngstr\xc3\xb6m', ['/dir1/Ångström', '/dir2/Ångström'])
            # Unicode strings are permitted.
            check_sources('Ångström', ['/dir1/Ångström', '/dir2/Ångström'])

    def test_utf8_bytestring(self):
        """
        Invalid UTF-8 encoding in bytestrings should raise a useful error
        """
        engine = Engine()
        loader = engine.template_loaders[0]
        with self.assertRaises(UnicodeDecodeError):
            list(loader.get_template_sources(b'\xc3\xc3', ['/dir1']))

    def test_unicode_dir_name(self):
        with self.source_checker([b'/Stra\xc3\x9fe']) as check_sources:
            check_sources('Ångström', ['/Straße/Ångström'])
            check_sources(b'\xc3\x85ngstr\xc3\xb6m', ['/Straße/Ångström'])

    @unittest.skipUnless(
        os.path.normcase('/TEST') == os.path.normpath('/test'),
        "This test only runs on case-sensitive file systems.",
    )
    def test_case_sensitivity(self):
        with self.source_checker(['/dir1', '/DIR2']) as check_sources:
            check_sources('index.html', ['/dir1/index.html', '/DIR2/index.html'])
            check_sources('/DIR1/index.HTML', ['/DIR1/index.HTML'])

    def test_file_does_not_exist(self):
        with self.assertRaises(TemplateDoesNotExist):
            self.engine.get_template('doesnotexist.html')

    @unittest.skipIf(
        sys.platform == 'win32',
        "Python on Windows doesn't have working os.chmod().",
    )
    def test_permissions_error(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            tmpdir = os.path.dirname(tmpfile.name)
            tmppath = os.path.join(tmpdir, tmpfile.name)
            os.chmod(tmppath, 0o0222)
            with self.set_dirs([tmpdir]):
                with self.assertRaisesMessage(IOError, 'Permission denied'):
                    self.engine.get_template(tmpfile.name)

    def test_notafile_error(self):
        with self.assertRaises(IOError):
            self.engine.get_template('first')

    def test_origin_uptodate(self):
        template = self.engine.get_template('index.html')
        self.assertTrue(template.origin.uptodate)
        os.utime(template.origin.name, None)
        self.assertFalse(template.origin.uptodate)

    def test_get_template_does_not_cache(self):
        template1 = self.engine.get_template('index.html')
        template2 = self.engine.get_template('index.html')
        self.assertFalse(template1 is template2)

class AppDirectoriesLoaderTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(
            loaders=['django.template.loaders.app_directories.Loader'],
        )
        super(AppDirectoriesLoaderTests, cls).setUpClass()

    @override_settings(INSTALLED_APPS=['template_tests'])
    def test_get_template(self):
        template = self.engine.get_template('index.html')
        self.assertEqual(template.origin.name, os.path.join(TEMPLATE_DIR, 'index.html'))
        self.assertEqual(template.origin.template_name, 'index.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0])

    @ignore_warnings(category=RemovedInDjango20Warning)
    @override_settings(INSTALLED_APPS=['template_tests'])
    def test_load_template_source(self):
        loader = self.engine.template_loaders[0]
        source, name = loader.load_template_source('index.html')
        self.assertEqual(source.strip(), 'index')
        self.assertEqual(name, os.path.join(TEMPLATE_DIR, 'index.html'))

    @override_settings(INSTALLED_APPS=[])
    def test_not_installed(self):
        with self.assertRaises(TemplateDoesNotExist):
            self.engine.get_template('index.html')


class LocmemLoaderTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(
            loaders=[('django.template.loaders.locmem.Loader', {
                'index.html': 'index',
            })],
        )
        super(LocmemLoaderTests, cls).setUpClass()

    def test_get_template(self):
        template = self.engine.get_template('index.html')
        self.assertEqual(template.origin.name, 'index.html')
        self.assertEqual(template.origin.template_name, 'index.html')
        self.assertEqual(template.origin.loader, self.engine.template_loaders[0])

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_load_template_source(self):
        loader = self.engine.template_loaders[0]
        source, name = loader.load_template_source('index.html')
        self.assertEqual(source.strip(), 'index')
        self.assertEqual(name, 'index.html')
