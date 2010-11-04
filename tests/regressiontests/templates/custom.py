from django import template
from django.utils.unittest import TestCase


class CustomTests(TestCase):
    def test_filter(self):
        t = template.Template("{% load custom %}{{ string|trim:5 }}")
        self.assertEqual(
            t.render(template.Context({"string": "abcdefghijklmnopqrstuvwxyz"})),
            u"abcde"
        )
