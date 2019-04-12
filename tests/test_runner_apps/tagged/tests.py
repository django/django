from unittest import TestCase

from django.test import tag


@tag("slow")
class TaggedTestCase(TestCase):
    @tag("fast")
    def test_single_tag(self):
        self.assertEqual(1, 1)

    @tag("fast", "core")
    def test_multiple_tags(self):
        self.assertEqual(1, 1)
