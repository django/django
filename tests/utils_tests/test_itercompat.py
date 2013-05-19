from django.test import TestCase

from .models import Category, Thing


class TestIsIterator(TestCase):
    def test_regression(self):
        """This failed on Django 1.5/Py2.6 because category has a next method."""
        category = Category.objects.create(name='category')
        Thing.objects.create(category=category)
        Thing.objects.filter(category=category)
