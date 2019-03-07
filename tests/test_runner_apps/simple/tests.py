from unittest import TestCase

from django.test import SimpleTestCase, TestCase as DjangoTestCase


class DjangoCase1(DjangoTestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class DjangoCase2(DjangoTestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class SimpleCase1(SimpleTestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class SimpleCase2(SimpleTestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class UnittestCase1(TestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class UnittestCase2(TestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass

    def test_3_test(self):
        pass
