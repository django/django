from unittest import TestCase

from mango.test import SimpleTestCase, TestCase as MangoTestCase


class MangoCase1(MangoTestCase):

    def test_1(self):
        pass

    def test_2(self):
        pass


class MangoCase2(MangoTestCase):

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
