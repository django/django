from unittest import TestCase

from django.test import TestCase as DjangoTestCase, TransactionTestCase


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


class TestTransactionTestCase3(TransactionTestCase):
    available_apps = ['test_discovery_sample3']
    serialized_rollback = False

    def test_sample(self):
        self.assertEqual(1, 1)
