from unittest import TestCase as UnitTestCase

from django.test import TestCase as DjangoTestCase
from django.utils.unittest import TestCase as UT2TestCase


class Test1(UnitTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class Test2(UT2TestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class Test3(DjangoTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)
