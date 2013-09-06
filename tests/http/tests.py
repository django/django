from django.utils import unittest
from django.test.client import RequestFactory

class HttpRequestTestCase(unittest.TestCase):
    """
    Regression tests for ticket # 18314.
    """
    def setUp(self):
        """
        Attaches a request factory.
        """
        self.factory = RequestFactory()

    def test_build_absolute_uri_no_location(self): #FIXME: it fails!
        """
        Ensures that ``request.build_absolute_uri()`` returns the proper value
        when the ``location`` argument is not provided, and ``request.path``
        begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////django-ate-my-baby')
        self.assertEqual(
            request.build_absolute_uri(),
            'http://testserver//django-ate-my-baby'
        )

    def test_build_absolute_uri_absolute_location(self):
        """
        Ensures that ``request.build_absolute_uri()`` returns the proper value
        when an absolute URL ``location`` argument is provided, and
        ``request.path`` begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////django-ate-my-baby')
        self.assertEqual(
            request.build_absolute_uri(location='http://example.com/?foo=bar'),
            'http://example.com/?foo=bar'
        )

    def test_build_absolute_uri_schema_relateive_location(self):
        """
        Ensures that ``request.build_absolute_uri()`` returns the proper value
        when a schema-relative URL ``location`` argument is provided, and
        ``request.path`` begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////django-ate-my-baby')
        self.assertEqual(
            request.build_absolute_uri(location='//example.com/?foo=bar'),
            'http://example.com/?foo=bar'
        )

    def test_build_absolute_uri_relative_location(self):
        """
        Ensures that ``request.build_absolute_uri()`` returns the proper value
        when a relative URL ``location`` argument is provided, and
        ``request.path`` begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////django-ate-my-baby')
        self.assertEqual(
            request.build_absolute_uri(location='/foo/bar/'),
            'http://testserver/foo/bar/'
        )
