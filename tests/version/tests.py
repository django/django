from unittest import skipUnless

import django.utils.version
from django import get_version
from django.test import SimpleTestCase
from django.utils.version import (
    get_complete_version,
    get_docs_version,
    get_git_changeset,
    get_main_version,
    get_version_tuple,
)


class VersionTests(SimpleTestCase):
    def test_development(self):
        get_git_changeset.cache_clear()
        ver_tuple = (1, 4, 0, "alpha", 0)
        # This will return a different result when it's run within or outside
        # of a git clone: 1.4.devYYYYMMDDHHMMSS or 1.4.
        ver_string = get_version(ver_tuple)
        self.assertRegex(ver_string, r"1\.4(\.dev[0-9]+)?")

        ver_tuple_calver = (2028, 0, 0, "alpha", 0)
        ver_string_calver = get_version(ver_tuple_calver)
        self.assertRegex(ver_string_calver, r"2028(\.dev[0-9]+)?")

    @skipUnless(
        hasattr(django.utils.version, "__file__"),
        "test_development() checks the same when __file__ is already missing, "
        "e.g. in a frozen environments",
    )
    def test_development_no_file(self):
        get_git_changeset.cache_clear()
        version_file = django.utils.version.__file__
        try:
            del django.utils.version.__file__
            self.test_development()
        finally:
            django.utils.version.__file__ = version_file

    def test_releases(self):
        tuples_to_strings = (
            ((1, 4, 0, "alpha", 1), "1.4a1"),
            ((1, 4, 0, "beta", 1), "1.4b1"),
            ((1, 4, 0, "rc", 1), "1.4rc1"),
            ((1, 4, 0, "final", 0), "1.4"),
            ((1, 4, 1, "rc", 2), "1.4.1rc2"),
            ((1, 4, 1, "final", 0), "1.4.1"),
            # CalVer (DEP 20)
            ((2028, 0, 0, "alpha", 1), "2028a1"),
            ((2028, 0, 0, "beta", 1), "2028b1"),
            ((2028, 0, 0, "rc", 1), "2028rc1"),
            ((2028, 0, 0, "final", 0), "2028"),
            ((2028, 1, 0, "rc", 2), "2028.1rc2"),
            ((2028, 1, 0, "final", 0), "2028.1"),
            ((2028, 5, 0, "final", 0), "2028.5"),
        )
        for ver_tuple, ver_string in tuples_to_strings:
            self.assertEqual(get_version(ver_tuple), ver_string)

    def test_get_main_version(self):
        tests = (
            ((1, 4, 0, "final", 0), "1.4"),
            ((1, 4, 1, "final", 0), "1.4.1"),
            ((2028, 0, 0, "final", 0), "2028"),
            ((2028, 1, 0, "final", 0), "2028.1"),
            ((2028, 5, 0, "final", 0), "2028.5"),
        )
        for ver_tuple, expected in tests:
            self.assertEqual(get_main_version(ver_tuple), expected)

    def test_get_docs_version(self):
        tests = (
            ((1, 4, 0, "alpha", 1), "dev"),
            ((1, 4, 0, "final", 0), "1.4"),
            ((1, 4, 1, "final", 0), "1.4"),
            ((2028, 0, 0, "alpha", 1), "dev"),
            ((2028, 0, 0, "final", 0), "2028"),
            ((2028, 1, 0, "final", 0), "2028"),
            ((2028, 5, 0, "final", 0), "2028"),
        )
        for ver_tuple, expected in tests:
            self.assertEqual(get_docs_version(ver_tuple), expected)

    def test_get_version_tuple(self):
        self.assertEqual(get_version_tuple("1.2.3"), (1, 2, 3))
        self.assertEqual(get_version_tuple("1.2.3b2"), (1, 2, 3))
        self.assertEqual(get_version_tuple("1.2.3b2.dev0"), (1, 2, 3))
        self.assertEqual(get_version_tuple("2028"), (2028,))
        self.assertEqual(get_version_tuple("2028.1"), (2028, 1))
        self.assertEqual(get_version_tuple("2028.1b2"), (2028, 1))
        self.assertEqual(get_version_tuple("2028.1b2.dev0"), (2028, 1))

    def test_get_version_invalid_version(self):
        tests = [
            # Invalid length.
            (3, 2, 0, "alpha", 1, "20210315111111"),
            # Invalid development status.
            (3, 2, 0, "gamma", 1, "20210315111111"),
        ]
        for version in tests:
            with self.subTest(version=version), self.assertRaises(AssertionError):
                get_complete_version(version)
