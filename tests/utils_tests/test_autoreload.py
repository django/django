import os

from django import conf
from django.contrib import admin
from django.core.apps import app_cache
from django.test import TestCase, override_settings
from django.utils.autoreload import gen_filenames

LOCALE_PATH = os.path.join(os.path.dirname(__file__), 'locale')


class TestFilenameGenerator(TestCase):
    def test_django_locales(self):
        """
        Test that gen_filenames() also yields the built-in django locale files.
        """
        filenames = list(gen_filenames())
        self.assertIn(os.path.join(os.path.dirname(conf.__file__), 'locale',
                                   'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)

    @override_settings(LOCALE_PATHS=(LOCALE_PATH,))
    def test_locale_paths_setting(self):
        """
        Test that gen_filenames also yields from LOCALE_PATHS locales.
        """
        filenames = list(gen_filenames())
        self.assertIn(os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)

    def test_project_root_locale(self):
        """
        Test that gen_filenames also yields from the current directory (project
        root).
        """
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(__file__))
        try:
            # Remove the current app from the app cache to guarantee that the
            # files will be found thanks to the current working directory.
            with app_cache._empty():
                filenames = list(gen_filenames())
            self.assertIn(
                os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo'),
                filenames)
        finally:
            os.chdir(old_cwd)

    def test_app_locales(self):
        """
        Test that gen_filenames also yields from locale dirs in installed apps.
        """
        with app_cache._empty(), app_cache._with_app('django.contrib.admin'):
            filenames = list(gen_filenames())
        self.assertIn(os.path.join(os.path.dirname(admin.__file__), 'locale',
                                   'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)

    @override_settings(USE_I18N=False)
    def test_no_i18n(self):
        """
        If i18n machinery is disabled, there is no need for watching the
        locale files.
        """
        filenames = list(gen_filenames())
        self.assertNotIn(
            os.path.join(os.path.dirname(conf.__file__), 'locale', 'nl',
                         'LC_MESSAGES', 'django.mo'),
            filenames)
