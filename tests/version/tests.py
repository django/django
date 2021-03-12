from django import get_version
from django.test import SimpleTestCase
from django.utils.version import get_complete_version, get_version_tuple


class VersionTests(SimpleTestCase):

    def test_development(self):
        ver_tuple = (1, 4, 0, 'alpha', 0)
        # This will return a different result when it's run within or outside
        # of a git clone: 1.4.devYYYYMMDDHHMMSS or 1.4.
        ver_string = get_version(ver_tuple)
        self.assertRegex(ver_string, r'1\.4(\.dev[0-9]+)?')

    def test_releases(self):
        tuples_to_strings = (
            ((1, 4, 0, 'alpha', 1), '1.4a1'),
            ((1, 4, 0, 'beta', 1), '1.4b1'),
            ((1, 4, 0, 'rc', 1), '1.4rc1'),
            ((1, 4, 0, 'final', 0), '1.4'),
            ((1, 4, 1, 'rc', 2), '1.4.1rc2'),
            ((1, 4, 1, 'final', 0), '1.4.1'),
        )
        for ver_tuple, ver_string in tuples_to_strings:
            self.assertEqual(get_version(ver_tuple), ver_string)

    def test_get_version_tuple(self):
        self.assertEqual(get_version_tuple('1.2.3'), (1, 2, 3))
        self.assertEqual(get_version_tuple('1.2.3b2'), (1, 2, 3))
        self.assertEqual(get_version_tuple('1.2.3b2.dev0'), (1, 2, 3))

    def test_get_version_invalid_version(self):
        tests = [
            # Invalid length.
            (3, 2, 0, 'alpha', 1, '20210315111111'),
            # Invalid development status.
            (3, 2, 0, 'gamma', 1, '20210315111111'),
        ]
        for version in tests:
            with self.subTest(version=version), self.assertRaises(AssertionError):
                get_complete_version(version)
