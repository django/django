 # -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime

from django.test import TestCase

from .models import Article, InternationalArticle


class SimpleTests(TestCase):
    def test_basic(self):
        a = Article.objects.create(
            headline=b'Area man programs in Python',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        self.assertEqual(str(a), b'Area man programs in Python')
        self.assertEqual(repr(a), b'<Article: Area man programs in Python>')

    def test_international(self):
        a = InternationalArticle.objects.create(
            headline='Girl wins €12.500 in lottery',
            pub_date=datetime.datetime(2005, 7, 28)
        )
        # The default str() output will be the UTF-8 encoded output of __unicode__().
        self.assertEqual(str(a), b'Girl wins \xe2\x82\xac12.500 in lottery')
