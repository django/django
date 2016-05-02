"""
Django Unit Test and Doctest framework.
"""

from django.test.client import Client, RequestFactory
from django.test.testcases import (
    LiveServerTestCase, SimpleTestCase, TestCase, TransactionTestCase,
    skipIfDBFeature, skipUnlessAnyDBFeature, skipUnlessDBFeature,
)
from django.test.utils import (
    ignore_warnings, modify_settings, override_settings,
    override_system_checks, tag,
)

__all__ = [
    'Client', 'RequestFactory', 'TestCase', 'TransactionTestCase',
    'SimpleTestCase', 'LiveServerTestCase', 'skipIfDBFeature',
    'skipUnlessAnyDBFeature', 'skipUnlessDBFeature', 'ignore_warnings',
    'modify_settings', 'override_settings', 'override_system_checks', 'tag',
]

# To simplify Django's test suite; not meant as a public API
try:
    from unittest import mock  # NOQA
except ImportError:
    try:
        import mock  # NOQA
    except ImportError:
        pass
