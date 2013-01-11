import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.simple import DjangoTestSuiteRunner, reorder_suite
from django.utils.importlib import import_module

try:
    from django.utils.unittest.loader import defaultTestLoader
except ImportError:
    try:
        from unittest2 import defaultTestLoader
    except ImportError:
        raise ImproperlyConfigured("Couldn't import unittest2 default "
                                   "test loader, install the unittest2 library.")


class DiscoverRunner(DjangoTestSuiteRunner):
    """A test suite runner that uses unittest2 test discovery."""
    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = None
        root = settings.TEST_DISCOVER_ROOT
        pattern = settings.TEST_DISCOVER_PATTERN
        top_level = settings.TEST_DISCOVER_TOP_LEVEL

        if test_labels:
            suite = defaultTestLoader.loadTestsFromNames(test_labels)
            # if single named module has no tests, do discovery within the
            # module itself
            if not suite.countTestCases() and len(test_labels) == 1:
                suite = None
                root = import_module(test_labels[0]).__path__[0]
                top_level = os.path.dirname(root)

        if suite is None:
            suite = defaultTestLoader.discover(root,
                pattern=pattern,
                top_level_dir=top_level,
                )

        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return reorder_suite(suite, (TestCase,))
