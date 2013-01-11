"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def test_basic_subtraction(self):
        """
        Tests that 2 - 1 always equals 1.
        """
        self.assertEqual(2 - 1, 1)

    def test_basic_subtraction_again(self):
        """
        Tests that 2 - 1 always equals 1.
        """
        self.assertEqual(2 - 1, 1)



class AnotherSimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)
