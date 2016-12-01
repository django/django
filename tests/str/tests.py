import datetime

from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps

from .models import InternationalArticle


class SimpleTests(TestCase):

    def test_international(self):
        a = InternationalArticle.objects.create(
            headline='Girl wins €12.500 in lottery',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        self.assertEqual(str(a), 'Girl wins €12.500 in lottery')

    @isolate_apps('str')
    def test_defaults(self):
        """
        The default implementation of __str__ and __repr__ should return
        instances of str.
        """
        class Default(models.Model):
            pass

        obj = Default()
        # Explicit call to __str__/__repr__ to make sure str()/repr() don't
        # coerce the returned value.
        self.assertIsInstance(obj.__str__(), str)
        self.assertIsInstance(obj.__repr__(), str)
        self.assertEqual(str(obj), str('Default object'))
        self.assertEqual(repr(obj), str('<Default: Default object>'))
