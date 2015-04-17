import os
import tempfile
from importlib import import_module

from django import conf
from django.contrib import admin
from django.test import SimpleTestCase, override_settings
from django.test.utils import extend_sys_path
from django.utils._os import npath, upath
from django.utils.autoreload import gen_filenames

LOCALE_PATH = os.path.join(os.path.dirname(__file__), 'locale')


class TestFilenameGenerator(SimpleTestCase):
    def setUp(self):
        # Empty cached variables
        from django.utils import autoreload
        autoreload._cached_modules = set()
        autoreload._cached_filenames = []

    def test_django_locales(self):
        """
        Test that gen_filenames() also yields the built-in django locale files.
        """
        filenames = list(gen_filenames())
        self.assertIn(os.path.join(os.path.dirname(conf.__file__), 'locale',
                                   'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)

    @override_settings(LOCALE_PATHS=[LOCALE_PATH])
    def test_locale_paths_setting(self):
        """
        Test that gen_filenames also yields from LOCALE_PATHS locales.
        """
        filenames = list(gen_filenames())
        self.assertIn(os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)

    @override_settings(INSTALLED_APPS=[])
    def test_project_root_locale(self):
        """
        Test that gen_filenames also yields from the current directory (project
        root).
        """
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(__file__))
        try:
            filenames = list(gen_filenames())
            self.assertIn(
                os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo'),
                filenames)
        finally:
            os.chdir(old_cwd)

    @override_settings(INSTALLED_APPS=['django.contrib.admin'])
    def test_app_locales(self):
        """
        Test that gen_filenames also yields from locale dirs in installed apps.
        """
        filenames = list(gen_filenames())
        self.assertIn(
            os.path.join(os.path.dirname(upath(admin.__file__)), 'locale', 'nl', 'LC_MESSAGES', 'django.mo'),
            filenames
        )

    @override_settings(USE_I18N=False)
    def test_no_i18n(self):
        """
        If i18n machinery is disabled, there is no need for watching the
        locale files.
        """
        filenames = list(gen_filenames())
        self.assertNotIn(
            os.path.join(os.path.dirname(upath(conf.__file__)), 'locale', 'nl', 'LC_MESSAGES', 'django.mo'),
            filenames
        )

    def test_only_new_files(self):
        """
        When calling a second time gen_filenames with only_new = True, only
        files from newly loaded modules should be given.
        """
        list(gen_filenames())
        from fractions import Fraction  # NOQA
        filenames2 = list(gen_filenames(only_new=True))
        self.assertEqual(len(filenames2), 1)
        self.assertTrue(filenames2[0].endswith('fractions.py'))
        self.assertFalse(any(f.endswith('.pyc') for f in gen_filenames()))

    def test_deleted_removed(self):
        dirname = tempfile.mkdtemp()
        filename = os.path.join(dirname, 'test_deleted_removed_module.py')
        with open(filename, 'w'):
            pass
        with extend_sys_path(dirname):
            import_module('test_deleted_removed_module')
        self.assertIn(npath(filename), gen_filenames())
        os.unlink(filename)
        self.assertNotIn(filename, gen_filenames())
