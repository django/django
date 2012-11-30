# -*- coding: utf-8 -*-
"""
Unit tests for {{ app_name|title }} Django application.

To check if tests pass run: `manage.py test`

.. seealso::
    http://docs.djangoproject.com/en/dev/topics/testing/
"""
from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)
