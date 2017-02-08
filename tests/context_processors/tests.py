"""
Tests for Django's bundled context processors.
"""
from django.test import SimpleTestCase, TestCase, override_settings


@override_settings(
    ROOT_URLCONF='context_processors.urls',
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    }],
)
class RequestContextProcessorTests(SimpleTestCase):
    """
    Tests for the ``django.template.context_processors.request`` processor.
    """

    def test_request_attributes(self):
        """
        The request object is available in the template and that its
        attributes can't be overridden by GET and POST parameters (#3828).
        """
        url = '/request_attrs/'
        # We should have the request object in the template.
        response = self.client.get(url)
        self.assertContains(response, 'Have request')
        # Test is_secure.
        response = self.client.get(url)
        self.assertContains(response, 'Not secure')
        response = self.client.get(url, {'is_secure': 'blah'})
        self.assertContains(response, 'Not secure')
        response = self.client.post(url, {'is_secure': 'blah'})
        self.assertContains(response, 'Not secure')
        # Test path.
        response = self.client.get(url)
        self.assertContains(response, url)
        response = self.client.get(url, {'path': '/blah/'})
        self.assertContains(response, url)
        response = self.client.post(url, {'path': '/blah/'})
        self.assertContains(response, url)


@override_settings(
    DEBUG=True,
    INTERNAL_IPS=['127.0.0.1'],
    ROOT_URLCONF='context_processors.urls',
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
            ],
        },
    }],
)
class DebugContextProcessorTests(TestCase):
    """
    Tests for the ``django.template.context_processors.debug`` processor.
    """
    multi_db = True

    def test_debug(self):
        url = '/debug/'
        # We should have the debug flag in the template.
        response = self.client.get(url)
        self.assertContains(response, 'Have debug')

        # And now we should not
        with override_settings(DEBUG=False):
            response = self.client.get(url)
            self.assertNotContains(response, 'Have debug')

    def test_sql_queries(self):
        """
        Test whether sql_queries represents the actual amount
        of queries executed. (#23364)
        """
        url = '/debug/'
        response = self.client.get(url)
        self.assertContains(response, 'First query list: 0')
        self.assertContains(response, 'Second query list: 1')
        # Check we have not actually memoized connection.queries
        self.assertContains(response, 'Third query list: 2')
        # Check queries for DB connection 'other'
        self.assertContains(response, 'Fourth query list: 3')
