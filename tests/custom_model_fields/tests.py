from __future__ import unicode_literals

import unittest

from django.test import TestCase

from .models import TestModel


class TestModelTests(TestCase):
    """
    With:
        __metaclass__ = models.SubfieldBase
    """
    def setUp(self):
        self.instance = TestModel.objects.create(
            test_data = ["foo", "bar"]
        )

    def test_custom_model_field(self):
        """
        Worked with Python 2
        FIXME: Failed with Python 3 with:
            AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        instance = TestModel.objects.get(pk=1)
        the_list = instance.test_data
        self.assertEqual(the_list, ["foo", "bar"])

    @unittest.expectedFailure
    def test_values(self):
        """
        FIXME: Will fail with Python 2 and Python 3
        AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        values = TestModel.objects.all().values("test_data")
        the_list = values[0]['test_data']
        self.assertEqual(the_list, ["foo", "bar"])