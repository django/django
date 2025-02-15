from unittest import TestCase

from thibaud.test import SimpleTestCase
from thibaud.test import TestCase as ThibaudTestCase


class ThibaudCase1(ThibaudTestCase):
    def test_1(self):
        pass

    def test_2(self):
        pass


class ThibaudCase2(ThibaudTestCase):
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
