# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from unittest import skipIf

from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps
from django.utils import six

from .models import Article, InternationalArticle


class SimpleTests(TestCase):

    @skipIf(six.PY3, "tests a __str__ method returning unicode under Python 2")
    def test_basic(self):
        a = Article.objects.create(
            headline=b'Parrot programs in Python',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        self.assertEqual(str(a), str('Parrot programs in Python'))
        self.assertEqual(repr(a), str('<Article: Parrot programs in Python>'))

    def test_international(self):
        a = InternationalArticle.objects.create(
            headline='Girl wins €12.500 in lottery',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        if six.PY3:
            self.assertEqual(str(a), 'Girl wins €12.500 in lottery')
        else:
            # On Python 2, the default str() output will be the UTF-8 encoded
            # output of __unicode__() -- or __str__() when the
            # python_2_unicode_compatible decorator is used.
            self.assertEqual(str(a), b'Girl wins \xe2\x82\xac12.500 in lottery')

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
