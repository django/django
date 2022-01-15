from django.template.defaultfilters import autoescape_aware
from django.test import SimpleTestCase


class AutoescapeAwareTests(SimpleTestCase):

    def test_autoescape_default(self):
        self.assertEqual(
            self.custom_filter('<p>test</p>'),
            '&lt;p&gt;test&lt;/p&gt;',
        )

    def test_autoescape_on(self):
        self.assertEqual(
            self.custom_filter('<p>test</p>', autoescape=True),
            '&lt;p&gt;test&lt;/p&gt;',
        )

    def test_autoescape_off(self):
        self.assertEqual(
            self.custom_filter('<p>test</p>', autoescape=False),
            '<p>test</p>',
        )

    @staticmethod
    @autoescape_aware
    def custom_filter(value, test=False, autoescape=True):
        return value
