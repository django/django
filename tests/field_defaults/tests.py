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
        self.assertNotEquals(first_comment.id, second_comment.id)
        for comment in (first_comment, second_comment):
            uuid_as_hex = comment.id.hex
            try:
                self.assertEquals(32, len(uuid_as_hex))
                self.assertEquals("4", uuid_as_hex[12])
            except AssertionError as exc:
                raise AssertionError(
                    "This id does not appear to be a valid UUID4 identifier: "
                    "{0}: {1}".format(uuid_as_hex, exc)
                )
