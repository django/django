# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path
import sys
import types
import unittest
from contextlib import contextmanager

from django.template import Context, TemplateDoesNotExist
from django.template.engine import Engine
from django.test import SimpleTestCase, override_settings
from django.utils import six

from .utils import TEMPLATE_DIR

try:
    import pkg_resources
except ImportError:
    pkg_resources = None


class CachedLoaderTests(SimpleTestCase):

    def create_engine(self, **kwargs):
        return Engine(
            loaders=[
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                ]),
            ],
        )

    def test_templatedir_caching(self):
        """
        #13573 -- Template directories should be part of the cache key.
        """
        engine = self.create_engine()

        # Retrieve a template specifying a template directory to check
        t1, name = engine.find_template('test.html', (os.path.join(TEMPLATE_DIR, 'first'),))
        # Now retrieve the same template name, but from a different directory
        t2, name = engine.find_template('test.html', (os.path.join(TEMPLATE_DIR, 'second'),))

        # The two templates should not have the same content
        self.assertNotEqual(t1.render(Context({})), t2.render(Context({})))

    def test_missing_template_is_cached(self):
        """
        #19949 -- TemplateDoesNotExist exceptions should be cached.
        """
        engine = self.create_engine()
        loader = engine.template_loaders[0]

        self.assertFalse('missing.html' in loader.template_cache)

        with self.assertRaises(TemplateDoesNotExist):
            loader.load_template("missing.html")

        self.assertEqual(
            loader.template_cache["missing.html"],
            TemplateDoesNotExist,
            "Cached loader failed to cache the TemplateDoesNotExist exception",
        )

    def test_debug_nodelist_name(self):
        template_name = 'index.html'
        engine = Engine(dirs=[TEMPLATE_DIR], debug=True)

        template = engine.get_template(template_name)
        name = template.nodelist[0].source[0].name
        self.assertTrue(
            name.endswith(template_name),
            'Template loaded through cached loader has incorrect name for debug page: %s' % template_name,
        )

        template = engine.get_template(template_name)
        name = template.nodelist[0].source[0].name
        self.assertTrue(
            name.endswith(template_name),
            'Cached template loaded through cached loader has incorrect name for debug page: %s' % template_name,
        )


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

    def setUp(self):
        engine = Engine(loaders=[
            'django.template.loaders.eggs.Loader',
        ])
        self.loader = engine.template_loaders[0]

    def test_existing(self):
        templates = {
            os.path.normcase('templates/y.html'): six.StringIO("y"),
        }

        with self.create_egg('egg', templates):
            with override_settings(INSTALLED_APPS=['egg']):
                contents, template_name = self.loader.load_template_source("y.html")
                self.assertEqual(contents, "y")
                self.assertEqual(template_name, "egg:egg:templates/y.html")

    def test_non_existing(self):
        """
        Template loading fails if the template is not in the egg.
        """
        with self.create_egg('egg', {}):
            with override_settings(INSTALLED_APPS=['egg']):
                with self.assertRaises(TemplateDoesNotExist):
                    self.loader.load_template_source("not-existing.html")

    def test_not_installed(self):
        """
        Template loading fails if the egg is not in INSTALLED_APPS.
        """
        templates = {
            os.path.normcase('templates/y.html'): six.StringIO("y"),
        }

        with self.create_egg('egg', templates):
            with self.assertRaises(TemplateDoesNotExist):
                self.loader.load_template_source("y.html")


class FileSystemLoaderTests(SimpleTestCase):

    def setUp(self):
        self.engine = Engine()

    @contextmanager
    def source_checker(self, dirs):
        loader = self.engine.template_loaders[0]

        def check_sources(path, expected_sources):
            expected_sources = [os.path.abspath(s) for s in expected_sources]
            self.assertEqual(
                list(loader.get_template_sources(path, dirs)),
                expected_sources,
            )

        yield check_sources

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


class AppDirectoriesLoaderTest(FileSystemLoaderTests):

    def setUp(self):
        self.engine = Engine(
            loaders=['django.template.loaders.app_directories.Loader'],
        )
