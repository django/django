# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from unittest import skipIf

from django.test import TestCase
from django.utils import six

from .models import Article, InternationalArticle


class SimpleTests(TestCase):

    @skipIf(six.PY3, "tests a __str__ method returning unicode under Python 2")
    def test_basic(self):
        a = Article.objects.create(
            headline=b'Area man programs in Python',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        self.assertEqual(str(a), str('Area man programs in Python'))
        self.assertEqual(repr(a), str('<Article: Area man programs in Python>'))

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
