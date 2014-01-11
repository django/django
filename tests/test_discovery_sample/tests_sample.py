from unittest import TestCase

from django.test import TestCase as DjangoTestCase


class TestVanillaUnittest(TestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class TestDjangoTestCase(DjangoTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class EmptyTestCase(TestCase):
    pass
