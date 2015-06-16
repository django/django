from __future__ import unicode_literals

from django.test import TestCase

from .models import TestModel1, TestModel2


class TestModel1Tests(TestCase):
    """
    Without:
        __metaclass__ = models.SubfieldBase
        
    https://docs.djangoproject.com/en/1.8/releases/1.8/#subfieldbase
    """
    def setUp(self):
        self.instance = TestModel1.objects.create(
            test_data = ["foo", "bar"]
        )

    def test_custom_model_field(self):
        """
        FIXME: Will fail with Python 2:
        AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        instance = TestModel1.objects.get(pk=1)
        the_list = instance.test_data
        self.assertEqual(the_list, ["foo", "bar"])

    def test_values(self):
        """
        FIXME: Will fail with Python 2 and Python 3
        AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        values = TestModel1.objects.all().values("test_data")
        the_list = values[0]['test_data']
        self.assertEqual(the_list, ["foo", "bar"])


class TestModel2Tests(TestCase):
    """
    With:
        __metaclass__ = models.SubfieldBase
    """
    def setUp(self):
        self.instance = TestModel2.objects.create(
            test_data = ["foo", "bar"]
        )

    def test_custom_model_field(self):
        """
        Worked with Python 2
        FIXME: Failed with Python 3 with:
            AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        instance = TestModel2.objects.get(pk=1)
        the_list = instance.test_data
        self.assertEqual(the_list, ["foo", "bar"])

    def test_values(self):
        """
        FIXME: Will fail with Python 2 and Python 3
        AssertionError: 'foo,bar' != ['foo', 'bar']
        """
        values = TestModel2.objects.all().values("test_data")
        the_list = values[0]['test_data']
        self.assertEqual(the_list, ["foo", "bar"])