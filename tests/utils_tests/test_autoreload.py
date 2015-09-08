import os
import shutil
import tempfile
from importlib import import_module

from django import conf
from django.contrib import admin
from django.test import SimpleTestCase, override_settings
from django.test.utils import extend_sys_path
from django.utils import autoreload
from django.utils._os import npath

LOCALE_PATH = os.path.join(os.path.dirname(__file__), 'locale')


class TestFilenameGenerator(SimpleTestCase):

    def clear_autoreload_caches(self):
        autoreload._cached_modules = set()
        autoreload._cached_filenames = []

    def assertFileFound(self, filename):
        self.clear_autoreload_caches()
        # Test uncached access
        self.assertIn(npath(filename), autoreload.gen_filenames())
        # Test cached access
        self.assertIn(npath(filename), autoreload.gen_filenames())

    def assertFileNotFound(self, filename):
        self.clear_autoreload_caches()
        # Test uncached access
        self.assertNotIn(npath(filename), autoreload.gen_filenames())
        # Test cached access
        self.assertNotIn(npath(filename), autoreload.gen_filenames())

    def assertFileFoundOnlyNew(self, filename):
        self.clear_autoreload_caches()
        # Test uncached access
        self.assertIn(npath(filename), autoreload.gen_filenames(only_new=True))
        # Test cached access
        self.assertNotIn(npath(filename), autoreload.gen_filenames(only_new=True))

    def test_django_locales(self):
        """
        Test that gen_filenames() yields the built-in Django locale files.
        """
        django_dir = os.path.join(os.path.dirname(conf.__file__), 'locale')
        django_mo = os.path.join(django_dir, 'nl', 'LC_MESSAGES', 'django.mo')
        self.assertFileFound(django_mo)

    @override_settings(LOCALE_PATHS=[LOCALE_PATH])
    def test_locale_paths_setting(self):
        """
        Test that gen_filenames also yields from LOCALE_PATHS locales.
        """
        locale_paths_mo = os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo')
        self.assertFileFound(locale_paths_mo)

    @override_settings(INSTALLED_APPS=[])
    def test_project_root_locale(self):
        """
        Test that gen_filenames also yields from the current directory (project
        root).
        """
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(__file__))
        current_dir = os.path.join(os.path.dirname(__file__), 'locale')
        current_dir_mo = os.path.join(current_dir, 'nl', 'LC_MESSAGES', 'django.mo')
        try:
            self.assertFileFound(current_dir_mo)
        finally:
            os.chdir(old_cwd)

    @override_settings(INSTALLED_APPS=['django.contrib.admin'])
    def test_app_locales(self):
        """
        Test that gen_filenames also yields from locale dirs in installed apps.
        """
        admin_dir = os.path.join(os.path.dirname(admin.__file__), 'locale')
        admin_mo = os.path.join(admin_dir, 'nl', 'LC_MESSAGES', 'django.mo')
        self.assertFileFound(admin_mo)

    @override_settings(USE_I18N=False)
    def test_no_i18n(self):
        """
        If i18n machinery is disabled, there is no need for watching the
        locale files.
        """
        django_dir = os.path.join(os.path.dirname(conf.__file__), 'locale')
        django_mo = os.path.join(django_dir, 'nl', 'LC_MESSAGES', 'django.mo')
        self.assertFileNotFound(django_mo)

    def test_paths_are_native_strings(self):
        for filename in autoreload.gen_filenames():
            self.assertIsInstance(filename, str)

    def test_only_new_files(self):
        """
        When calling a second time gen_filenames with only_new = True, only
        files from newly loaded modules should be given.
        """
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_only_new_module.py')
        self.addCleanup(shutil.rmtree, dirname)
        with open(filename, 'w'):
            pass

        # Test uncached access
        self.clear_autoreload_caches()
        filenames = set(autoreload.gen_filenames(only_new=True))
        filenames_reference = set(autoreload.gen_filenames())
        self.assertEqual(filenames, filenames_reference)

        # Test cached access: no changes
        filenames = set(autoreload.gen_filenames(only_new=True))
        self.assertEqual(filenames, set())

        # Test cached access: add a module
        with extend_sys_path(dirname):
            import_module('test_only_new_module')
        filenames = set(autoreload.gen_filenames(only_new=True))
        self.assertEqual(filenames, {npath(filename)})

    def test_deleted_removed(self):
        """
        When a file is deleted, gen_filenames() no longer returns it.
        """
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_deleted_removed_module.py')
        self.addCleanup(shutil.rmtree, dirname)
        with open(filename, 'w'):
            pass

        with extend_sys_path(dirname):
            import_module('test_deleted_removed_module')
        self.assertFileFound(filename)

        os.unlink(filename)
        self.assertFileNotFound(filename)

    def test_check_errors(self):
        """
        When a file containing an error is imported in a function wrapped by
        check_errors(), gen_filenames() returns it.
        """
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_syntax_error.py')
        self.addCleanup(shutil.rmtree, dirname)
        with open(filename, 'w') as f:
            f.write("Ceci n'est pas du Python.")

        with extend_sys_path(dirname):
            with self.assertRaises(SyntaxError):
                autoreload.check_errors(import_module)('test_syntax_error')
        self.assertFileFound(filename)

    def test_check_errors_only_new(self):
        """
        When a file containing an error is imported in a function wrapped by
        check_errors(), gen_filenames(only_new=True) returns it.
        """
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_syntax_error.py')
        self.addCleanup(shutil.rmtree, dirname)
        with open(filename, 'w') as f:
            f.write("Ceci n'est pas du Python.")

        with extend_sys_path(dirname):
            with self.assertRaises(SyntaxError):
                autoreload.check_errors(import_module)('test_syntax_error')
        self.assertFileFoundOnlyNew(filename)

    def test_check_errors_catches_all_exceptions(self):
        """
        Since Python may raise arbitrary exceptions when importing code,
        check_errors() must catch Exception, not just some subclasses.
        """
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_exception.py')
        self.addCleanup(shutil.rmtree, dirname)
        with open(filename, 'w') as f:
            f.write("raise Exception")

        with extend_sys_path(dirname):
            with self.assertRaises(Exception):
                autoreload.check_errors(import_module)('test_exception')
        self.assertFileFound(filename)
