from datetime import datetime

from django.test import TestCase
from django.utils import six

from .models import Article, Comment


class DefaultTests(TestCase):
    def test_field_defaults(self):
        a = Article()
        now = datetime.now()
        a.save()

        self.assertIsInstance(a.id, six.integer_types)
        self.assertEqual(a.headline, "Default headline")
        self.assertTrue((now - a.pub_date).seconds < 5)

    def test_uuid_field_defaults(self):
        first_comment = Comment()
        second_comment = Comment()

        self.assertNotEqual(first_comment.id, second_comment.id)
        for comment in (first_comment, second_comment):
            uuid_as_hex = comment.id.hex
            msg = "This id does not seem to be a valid UUID4 identifier: {}"
            self.assertEqual("4", uuid_as_hex[12], msg=msg.format(uuid_as_hex))
