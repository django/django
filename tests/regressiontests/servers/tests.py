"""
Tests for django.core.servers.
"""
import os
from urlparse import urljoin
import urllib2

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, LiveServerTestCase
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler, WSGIServerException
from django.test.utils import override_settings

from .models import Person

class AdminMediaHandlerTests(TestCase):

    def setUp(self):
        self.admin_media_url = urljoin(settings.STATIC_URL, 'admin/')
        self.admin_media_file_path = os.path.abspath(
            os.path.join(django.__path__[0], 'contrib', 'admin', 'static', 'admin')
        )
        self.handler = AdminMediaHandler(WSGIHandler())

    def test_media_urls(self):
        """
        Tests that URLs that look like absolute file paths after the
        settings.STATIC_URL don't turn into absolute file paths.
        """
        # Cases that should work on all platforms.
        data = (
            ('%scss/base.css' % self.admin_media_url, ('css', 'base.css')),
        )
        # Cases that should raise an exception.
        bad_data = ()

        # Add platform-specific cases.
        if os.sep == '/':
            data += (
                # URL, tuple of relative path parts.
                ('%s\\css/base.css' % self.admin_media_url, ('\\css', 'base.css')),
            )
            bad_data += (
                '%s/css/base.css' % self.admin_media_url,
                '%s///css/base.css' % self.admin_media_url,
                '%s../css/base.css' % self.admin_media_url,
            )
        elif os.sep == '\\':
            bad_data += (
                '%sC:\css/base.css' % self.admin_media_url,
                '%s/\\css/base.css' % self.admin_media_url,
                '%s\\css/base.css' % self.admin_media_url,
                '%s\\\\css/base.css' % self.admin_media_url
            )
        for url, path_tuple in data:
            try:
                output = self.handler.file_path(url)
            except ValueError:
                self.fail("Got a ValueError exception, but wasn't expecting"
                          " one. URL was: %s" % url)
            rel_path = os.path.join(*path_tuple)
            desired = os.path.join(self.admin_media_file_path, rel_path)
            self.assertEqual(
                os.path.normcase(output), os.path.normcase(desired),
                "Got: %s, Expected: %s, URL was: %s" % (output, desired, url))
        for url in bad_data:
            try:
                output = self.handler.file_path(url)
            except ValueError:
                continue
            self.fail('URL: %s should have caused a ValueError exception.'
                      % url)


TEST_ROOT = os.path.dirname(__file__)
TEST_SETTINGS = {
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'media'),
    'STATIC_URL': '/static/',
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'static'),
}


class LiveServerBase(LiveServerTestCase):
    urls = 'regressiontests.servers.urls'
    fixtures = ['testdata.json']

    @classmethod
    def setUpClass(cls):
        # Override settings
        cls.settings_override = override_settings(**TEST_SETTINGS)
        cls.settings_override.enable()
        super(LiveServerBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Restore original settings
        cls.settings_override.disable()
        super(LiveServerBase, cls).tearDownClass()

    def urlopen(self, url):
        return urllib2.urlopen(self.live_server_url + url)


class LiveServerAddress(LiveServerBase):
    """
    Ensure that the address set in the environment variable is valid.
    Refs #2879.
    """

    @classmethod
    def setUpClass(cls):
        # Backup original environment variable
        address_predefined = 'DJANGO_LIVE_TEST_SERVER_ADDRESS' in os.environ
        old_address = os.environ.get('DJANGO_LIVE_TEST_SERVER_ADDRESS')

        # Just the host is not accepted
        cls.raises_exception('localhost', ImproperlyConfigured)

        # The host must be valid
        cls.raises_exception('blahblahblah:8081', WSGIServerException)

        # The list of ports must be in a valid format
        cls.raises_exception('localhost:8081,', ImproperlyConfigured)
        cls.raises_exception('localhost:8081,blah', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-blah', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-8082-8083', ImproperlyConfigured)

        # If contrib.staticfiles isn't configured properly, the exception
        # should bubble up to the main thread.
        old_STATIC_URL = TEST_SETTINGS['STATIC_URL']
        TEST_SETTINGS['STATIC_URL'] = None
        cls.raises_exception('localhost:8081', ImproperlyConfigured)
        TEST_SETTINGS['STATIC_URL'] = old_STATIC_URL

        # Restore original environment variable
        if address_predefined:
            os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = old_address
        else:
            del os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS']

    @classmethod
    def raises_exception(cls, address, exception):
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = address
        try:
            super(LiveServerAddress, cls).setUpClass()
            raise Exception("The line above should have raised an exception")
        except exception:
            pass

    def test_test_test(self):
        # Intentionally empty method so that the test is picked up by the
        # test runner and the overriden setUpClass() method is executed.
        pass

class LiveServerViews(LiveServerBase):
    def test_404(self):
        """
        Ensure that the LiveServerTestCase serves 404s.
        Refs #2879.
        """
        try:
            self.urlopen('/')
        except urllib2.HTTPError, err:
            self.assertEquals(err.code, 404, 'Expected 404 response')
        else:
            self.fail('Expected 404 response')

    def test_view(self):
        """
        Ensure that the LiveServerTestCase serves views.
        Refs #2879.
        """
        f = self.urlopen('/example_view/')
        self.assertEquals(f.read(), 'example view')

    def test_static_files(self):
        """
        Ensure that the LiveServerTestCase serves static files.
        Refs #2879.
        """
        f = self.urlopen('/static/example_static_file.txt')
        self.assertEquals(f.read(), 'example static file\n')

    def test_media_files(self):
        """
        Ensure that the LiveServerTestCase serves media files.
        Refs #2879.
        """
        f = self.urlopen('/media/example_media_file.txt')
        self.assertEquals(f.read(), 'example media file\n')


class LiveServerDatabase(LiveServerBase):

    def test_fixtures_loaded(self):
        """
        Ensure that fixtures are properly loaded and visible to the
        live server thread.
        Refs #2879.
        """
        f = self.urlopen('/model_view/')
        self.assertEquals(f.read().splitlines(), ['jane', 'robert'])

    def test_database_writes(self):
        """
        Ensure that data written to the database by a view can be read.
        Refs #2879.
        """
        self.urlopen('/create_model_instance/')
        names = [person.name for person in Person.objects.all()]
        self.assertEquals(names, ['jane', 'robert', 'emily'])
