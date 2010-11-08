from unittest import TestCase

from django import template


class CustomTests(TestCase):
    def test_filter(self):
        t = template.Template("{% load custom %}{{ string|trim:5 }}")
        self.assertEqual(
            t.render(template.Context({"string": "abcdefghijklmnopqrstuvwxyz"})),
            u"abcde"
        )
