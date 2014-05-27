from datetime import datetime

from freedom.test import TestCase
from freedom.utils import six

from .models import Article


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, six.integer_types)
        self.assertEqual(a.headline, "Default headline")
        self.assertTrue((now - a.pub_date).seconds < 5)
