from unittest import TestCase as UnitTestCase

from django.test import TestCase as DjangoTestCase
from django.utils.unittest import TestCase as UT2TestCase


class TestVanillaUnittest(UnitTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class TestUnittest2(UT2TestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class TestDjangoTestCase(DjangoTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)
