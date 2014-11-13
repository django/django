from datetime import datetime

from django.test import TestCase
from django.utils import six

from .models import Article


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, six.integer_types)
        self.assertEqual(a.headline, "Default headline")
        self.assertLess((now - a.pub_date).seconds, 5)
