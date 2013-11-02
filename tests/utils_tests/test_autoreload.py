import os

from django import conf
from django.test import TestCase, override_settings
from django.utils.autoreload import gen_filenames

LOCALE_PATH = os.path.join(os.path.dirname(__file__), 'locale')


class TestFilenameGenerator(TestCase):
    def test_django_locales(self):
        """
        Test that gen_filenames() also yields the built-in django locale files.
        """
        filenames = list(gen_filenames())
        locales = []

        basedir = os.path.join(os.path.dirname(conf.__file__), 'locale')
        for dirpath, dirnames, locale_filenames in os.walk(basedir):
            for filename in locale_filenames:
                if filename.endswith('.mo'):
                    locales.append(os.path.join(dirpath, filename))

        self.assertTrue(len(locales) > 10)  # assume a few available locales
        for filename in locales:
            self.assertIn(filename, filenames)

    @override_settings(
        LOCALE_PATHS=(LOCALE_PATH,)
    )
    def test_app_locales(self):
        """
        Test that gen_filenames also yields from LOCALE_PATHS.
        """
        filenames = list(gen_filenames())
        self.assertIn(os.path.join(LOCALE_PATH, 'nl', 'LC_MESSAGES', 'django.mo'),
                      filenames)
