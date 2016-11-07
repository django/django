from unittest import TestCase

from django.test import (
    SimpleTestCase, TestCase as DjangoTestCase, TransactionTestCase,
)


class TestDjangoTestCase(DjangoTestCase):
    def test_sample(self):
        self.assertEqual(1, 1)


class TestVanillaUnittest(TestCase):
    def test_sample(self):
        self.assertEqual(1, 1)


class TestZimpleTestCase(SimpleTestCase):
    # Z gets this test to appear after Vanilla in the default suite.
    def test_sample(self):
        self.assertEqual(1, 1)


class TestTransactionTestCase(TransactionTestCase):
    available_apps = ['test_discovery_sample3']

    def test_sample(self):
        self.assertEqual(1, 1)
