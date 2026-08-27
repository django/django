import os
from pathlib import Path

import django
from django.test import SimpleTestCase
from django.utils.warnings import django_file_prefixes


class DjangoFilePrefixesTests(SimpleTestCase):
    def setUp(self):
        django_file_prefixes.cache_clear()
        self.addCleanup(django_file_prefixes.cache_clear)

    def test_no_file(self):
        orig_file = django.__file__
        try:
            # Depending on the cwd, Python might give a local checkout
            # precedence over installed Django, producing None.
            django.__file__ = None
            self.assertEqual(django_file_prefixes(), ())
            del django.__file__
            self.assertEqual(django_file_prefixes(), ())
        finally:
            django.__file__ = orig_file

    def test_with_file(self):
        prefixes = django_file_prefixes()
        self.assertIsInstance(prefixes, tuple)
        self.assertEqual(len(prefixes), 1)
        self.assertTrue(prefixes[0].endswith(f"{os.path.sep}django{os.path.sep}"))

    def test_does_not_match_packages_prefixed_with_django(self):
        other_file = Path(django.__file__).parent.parent / "djangoextra" / "__init__.py"
        self.assertFalse(str(other_file).startswith(django_file_prefixes()))
