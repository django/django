from __future__ import absolute_import

from django.test import TestCase

from .models import Guitarist


class PermalinkTests(TestCase):
    urls = 'regressiontests.model_permalink.urls'

    def test_permalink(self):
        g = Guitarist(name='Adrien Moignard', slug='adrienmoignard')
        self.assertEqual(g.url(), '/guitarists/adrienmoignard/')

    def test_wrapped_docstring(self):
        "Methods using the @permalink decorator retain their docstring."
        g = Guitarist(name='Adrien Moignard', slug='adrienmoignard')
        self.assertEqual(g.url.__doc__, "Returns the URL for this guitarist.")

    def test_wrapped_attribute(self):
        """
        Methods using the @permalink decorator can have attached attributes
        from other decorators
        """
        g = Guitarist(name='Adrien Moignard', slug='adrienmoignard')
        self.assertTrue(hasattr(g.url_with_attribute, 'attribute'))
        self.assertEqual(g.url_with_attribute.attribute, 'value')
