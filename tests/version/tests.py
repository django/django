import copy
import operator
import pickle
from unittest import skipUnless

import django
import django.utils.version
from django import get_version
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango2028Warning
from django.utils.version import (
    VersionTuple,
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
        )
        for ver_tuple, ver_string in tuples_to_strings:
            self.assertEqual(get_version(ver_tuple), ver_string)

    def test_calendar_development(self):
        get_git_changeset.cache_clear()
        ver_tuple = (2029, 0, "alpha", 0)
        # This will return a different result when it's run within or outside
        # of a git clone: 2029.devYYYYMMDDHHMMSS or 2029.
        ver_string = get_version(ver_tuple)
        self.assertRegex(ver_string, r"2029(\.dev[0-9]+)?")

    def test_calendar_releases(self):
        tuples_to_strings = (
            ((2028, 0, "alpha", 1), "2028a1"),
            ((2028, 0, "beta", 1), "2028b1"),
            ((2028, 0, "rc", 1), "2028rc1"),
            ((2028, 0, "final", 0), "2028"),
            ((2028, 1, "final", 0), "2028.1"),
            ((2028, 15, "final", 0), "2028.15"),
            ((2030, 2, "final", 0), "2030.2"),
        )
        for ver_tuple, ver_string in tuples_to_strings:
            with self.subTest(version=ver_tuple):
                self.assertEqual(get_version(ver_tuple), ver_string)

    def test_get_main_version(self):
        cases = [
            ((1, 4, 0, "alpha", 1), "1.4"),
            ((1, 4, 0, "final", 0), "1.4"),
            ((1, 4, 1, "final", 0), "1.4.1"),
            ((2028, 0, "alpha", 1), "2028"),
            ((2028, 0, "final", 0), "2028"),
            ((2028, 1, "final", 0), "2028.1"),
            ((2028, 15, "final", 0), "2028.15"),
        ]
        for ver_tuple, expected in cases:
            with self.subTest(version=ver_tuple):
                self.assertEqual(get_main_version(ver_tuple), expected)

    def test_get_docs_version(self):
        cases = [
            ((1, 4, 0, "alpha", 1), "dev"),
            ((1, 4, 0, "final", 0), "1.4"),
            ((1, 4, 1, "final", 0), "1.4"),
            ((2028, 0, "alpha", 1), "dev"),
            ((2028, 0, "final", 0), "2028"),
            ((2028, 1, "final", 0), "2028"),
            ((2028, 15, "final", 0), "2028"),
        ]
        for ver_tuple, expected in cases:
            with self.subTest(version=ver_tuple):
                self.assertEqual(get_docs_version(ver_tuple), expected)

    def test_get_version_tuple(self):
        self.assertEqual(get_version_tuple("1.2.3"), (1, 2, 3))
        self.assertEqual(get_version_tuple("1.2.3b2"), (1, 2, 3))
        self.assertEqual(get_version_tuple("1.2.3b2.dev0"), (1, 2, 3))
        self.assertEqual(get_version_tuple("2028"), (2028,))
        self.assertEqual(get_version_tuple("2028.1"), (2028, 1))
        self.assertEqual(get_version_tuple("2028b2"), (2028,))

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


class VersionTupleTests(SimpleTestCase):

    # The deprecation only applies to versions in the X.Y[.Z] scheme, whose
    # tuple loses a component when calendar versions arrive.
    version = VersionTuple(6, 2, 1, "final", 0)
    calendar_version = VersionTuple(2028, 5, "final", 0)
    # RemovedInDjango2028Warning.
    hint = "django.VERSION has four components from Django 2028"

    def test_attributes(self):
        cases = [
            ((6, 2, 0, "alpha", 1), (6, 2), 0, "alpha", 1),
            ((6, 2, 0, "final", 0), (6, 2), 0, "final", 0),
            ((6, 2, 1, "final", 0), (6, 2), 1, "final", 0),
            ((1, 11, 29, "final", 0), (1, 11), 29, "final", 0),
            ((2028, 0, "alpha", 1), (2028,), 0, "alpha", 1),
            ((2028, 0, "final", 0), (2028,), 0, "final", 0),
            ((2028, 5, "final", 0), (2028,), 5, "final", 0),
        ]
        for version, feature, patch, status, iteration in cases:
            version = VersionTuple(*version)
            with self.subTest(version=version):
                self.assertEqual(version.feature, feature)
                self.assertEqual(version.patch, patch)
                self.assertEqual(version.status, status)
                self.assertEqual(version.iteration, iteration)

    def test_feature_comparisons_span_both_schemes(self):
        self.assertIs(self.version.feature >= (5, 2), True)
        self.assertIs(self.version.feature == (6, 2), True)
        self.assertIs(self.calendar_version.feature >= (5, 2), True)
        self.assertIs(self.calendar_version.feature == (2028,), True)
        self.assertIs(self.calendar_version.feature < (2029,), True)

    def test_django_version_is_a_version_tuple(self):
        self.assertIsInstance(django.VERSION, VersionTuple)
        # RemovedInDjango2028Warning: remove the rest of this test.
        msg = "Indexing django.VERSION from its third component"
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            django.VERSION[2]

    def test_invalid_version(self):
        cases = [
            # Too few or too many components.
            (6, 2, "final"),
            (6, 2, 0, "final", 0, 0),
            (2028, 5, "final"),
            (2028, 5, 0, "final", 0, 0),
            # The status is not where it belongs, second to last.
            (6, 2, 0, "final"),
            # Invalid development status.
            (6, 2, 0, "gamma", 0),
            (2028, 5, "gamma", 0),
        ]
        for version in cases:
            with self.subTest(version=version), self.assertRaises(AssertionError):
                VersionTuple(*version)

    # RemovedInDjango2028Warning.
    def test_indexing_from_third_component_deprecated(self):
        msg = "Indexing django.VERSION from its third component on"
        indexes = [
            2,
            3,
            4,
            -1,
            -2,
            -3,
            slice(3),
            slice(None),
            slice(1, None),
            slice(None, None, 2),
        ]
        for index in indexes:
            with self.subTest(index=index):
                with self.assertWarnsMessage(RemovedInDjango2028Warning, msg) as ctx:
                    self.version[index]
                self.assertIn(self.hint, str(ctx.warning))

    # RemovedInDjango2028Warning.
    def test_indexing_first_two_components_not_deprecated(self):
        cases = [
            (0, 6),
            (1, 2),
            (-4, 2),
            (-5, 6),
            (slice(2), (6, 2)),
            (slice(1), (6,)),
            (slice(0, 2), (6, 2)),
        ]
        for index, expected in cases:
            with self.subTest(index=index):
                self.assertEqual(self.version[index], expected)

    # RemovedInDjango2028Warning.
    def test_iterating_deprecated(self):
        msg = "Iterating or unpacking django.VERSION is deprecated."
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            major, minor, micro, status, iteration = self.version
        self.assertEqual(
            (major, minor, micro, status, iteration), (6, 2, 1, "final", 0)
        )
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            self.assertEqual(tuple(self.version), (6, 2, 1, "final", 0))
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            self.assertEqual(list(self.version), [6, 2, 1, "final", 0])

    # RemovedInDjango2028Warning.
    def test_length_deprecated(self):
        msg = "Relying on the length of django.VERSION is deprecated."
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            self.assertEqual(len(self.version), 5)

    # RemovedInDjango2028Warning.
    def test_comparison_with_three_or_more_components_deprecated(self):
        msg = "Comparing django.VERSION with three or more components is deprecated."
        operators = [
            operator.eq,
            operator.ne,
            operator.lt,
            operator.le,
            operator.gt,
            operator.ge,
        ]
        for other in [(6, 2, 1), (6, 2, 1, "final", 0)]:
            for op in operators:
                with self.subTest(other=other, operator=op.__name__):
                    with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
                        op(self.version, other)

    # RemovedInDjango2028Warning.
    def test_reflected_comparison_deprecated(self):
        msg = "Comparing django.VERSION with three or more components is deprecated."
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            self.assertIs((6, 2, 1, "final", 0) == self.version, True)

    # RemovedInDjango2028Warning.
    def test_comparison_with_fewer_components_not_deprecated(self):
        cases = [
            (operator.ge, (6,), True),
            (operator.ge, (6, 2), True),
            (operator.ge, (6, 3), False),
            (operator.lt, (2028,), True),
            (operator.eq, (6, 2), False),
            (operator.ne, (6, 2), True),
        ]
        for op, other, expected in cases:
            with self.subTest(operator=op.__name__, other=other):
                self.assertIs(op(self.version, other), expected)

    # RemovedInDjango2028Warning.
    def test_comparison_with_non_tuple_not_deprecated(self):
        self.assertIs(self.version == "6.2.1", False)

    # RemovedInDjango2028Warning.
    def test_calendar_versions_not_deprecated(self):
        # Calendar versions already have their final shape, so nothing about
        # reading them is deprecated.
        self.assertEqual(self.calendar_version[1], 5)
        self.assertEqual(self.calendar_version[2], "final")
        self.assertEqual(self.calendar_version[:], (2028, 5, "final", 0))
        self.assertEqual(len(self.calendar_version), 4)
        self.assertEqual(tuple(self.calendar_version), (2028, 5, "final", 0))
        self.assertIs(self.calendar_version == (2028, 5, "final", 0), True)

    def test_hashing(self):
        self.assertEqual(hash(self.version), hash((6, 2, 1, "final", 0)))

    def test_repr(self):
        self.assertEqual(repr(self.version), "(6, 2, 1, 'final', 0)")
        self.assertEqual(repr(self.calendar_version), "(2028, 5, 'final', 0)")

    def test_copying_and_pickling(self):
        # These go through __getnewargs__(), which must unpack the components
        # for the __new__() signature.
        for label, restore in [
            ("pickle", lambda v: pickle.loads(pickle.dumps(v))),
            ("copy", copy.copy),
            ("deepcopy", copy.deepcopy),
        ]:
            for version in [self.version, self.calendar_version]:
                with self.subTest(label, version=version):
                    restored = restore(version)
                    self.assertIsInstance(restored, VersionTuple)
                    self.assertEqual(restored.feature, version.feature)
                    self.assertEqual(restored.patch, version.patch)
                    self.assertEqual(restored.status, version.status)
                    self.assertEqual(restored.iteration, version.iteration)

    def test_version_helpers(self):
        cases = [
            ((6, 2, 1, "final", 0), "6.2.1", "6.2.1", "6.2"),
            ((2028, 0, "alpha", 1), "2028a1", "2028", "dev"),
            ((2028, 0, "rc", 2), "2028rc2", "2028", "dev"),
            ((2028, 0, "final", 0), "2028", "2028", "2028"),
            ((2028, 5, "final", 0), "2028.5", "2028.5", "2028"),
            ((2030, 12, "final", 0), "2030.12", "2030.12", "2030"),
        ]
        for version, expected, main, docs in cases:
            version = VersionTuple(*version)
            with self.subTest(version=version):
                self.assertIs(get_complete_version(version), version)
                self.assertEqual(get_version(version), expected)
                self.assertEqual(get_main_version(version), main)
                self.assertEqual(get_docs_version(version), docs)
