from unittest import TestCase

from django.test import (
    TestCase as DjangoTestCase, TransactionTestCase, skipUnlessDBFeature,
)


class TestVanillaUnittest(TestCase):
    def test_sample(self):
        self.assertEqual(1, 1)


class TestDjangoTestCase(DjangoTestCase):
    def test_sample(self):
        self.assertEqual(1, 1)


class TestTransactionTestCase1(TransactionTestCase):
    available_apps = ['test_discovery_sample3']
    serialized_rollback = False

    def test_sample(self):
        self.assertEqual(1, 1)


class TestTransactionTestCase2(TransactionTestCase):
    available_apps = ['test_discovery_sample3']
    serialized_rollback = True

    def test_sample(self):
        self.assertEqual(1, 1)


# django.test.runner.reorder_postprocess() ignores this skipped test when
# assigning _next_serialized_rollback.
@skipUnlessDBFeature('nonexistent')
class TestTransactionTestCase3(TransactionTestCase):
    available_apps = ['test_discovery_sample3']
    serialized_rollback = True

    def test_sample(self):
        self.assertEqual(1, 1)


class TestTransactionTestCase4(TransactionTestCase):
    available_apps = ['test_discovery_sample3']
    serialized_rollback = False

    def test_sample(self):
        self.assertEqual(1, 1)
