from __future__ import absolute_import

from datetime import datetime

from django.test import TestCase
from django.utils.py3 import integer_types

from .models import Article


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertTrue(isinstance(a.id, integer_types))
        self.assertEqual(a.headline, "Default headline")
        self.assertTrue((now - a.pub_date).seconds < 5)
