# -*- encoding: utf-8 -*-
"""
Tests for django.core.servers.
"""
from __future__ import unicode_literals

import os
import socket

from django.core.exceptions import ImproperlyConfigured
from django.test import LiveServerTestCase, override_settings
from django.utils._os import upath
from django.utils.http import urlencode
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.request import urlopen

from .models import Person

TEST_ROOT = os.path.dirname(upath(__file__))
TEST_SETTINGS = {
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'media'),
    'STATIC_URL': '/static/',
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'static'),
}


@override_settings(ROOT_URLCONF='servers.urls', **TEST_SETTINGS)
class LiveServerBase(LiveServerTestCase):

    available_apps = [
        'servers',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
    ]
    fixtures = ['testdata.json']

    def urlopen(self, url):
        return urlopen(self.live_server_url + url)


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
        cls.raises_exception('blahblahblah:8081', socket.error)

        # The list of ports must be in a valid format
        cls.raises_exception('localhost:8081,', ImproperlyConfigured)
        cls.raises_exception('localhost:8081,blah', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-blah', ImproperlyConfigured)
        cls.raises_exception('localhost:8081-8082-8083', ImproperlyConfigured)

        # Restore original environment variable
        if address_predefined:
            os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = old_address
        else:
            del os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS']

    @classmethod
    def tearDownClass(cls):
        # skip it, as setUpClass doesn't call its parent either
        pass

    @classmethod
    def raises_exception(cls, address, exception):
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = address
        try:
            super(LiveServerAddress, cls).setUpClass()
            raise Exception("The line above should have raised an exception")
        except exception:
            pass
        finally:
            super(LiveServerAddress, cls).tearDownClass()

    def test_test_test(self):
        # Intentionally empty method so that the test is picked up by the
        # test runner and the overridden setUpClass() method is executed.
        pass


class LiveServerViews(LiveServerBase):
    def test_404(self):
        """
        Ensure that the LiveServerTestCase serves 404s.
        Refs #2879.
        """
        try:
            self.urlopen('/')
        except HTTPError as err:
            self.assertEqual(err.code, 404, 'Expected 404 response')
        else:
            self.fail('Expected 404 response')

    def test_view(self):
        """
        Ensure that the LiveServerTestCase serves views.
        Refs #2879.
        """
        f = self.urlopen('/example_view/')
        self.assertEqual(f.read(), b'example view')

    def test_static_files(self):
        """
        Ensure that the LiveServerTestCase serves static files.
        Refs #2879.
        """
        f = self.urlopen('/static/example_static_file.txt')
        self.assertEqual(f.read().rstrip(b'\r\n'), b'example static file')

    def test_no_collectstatic_emulation(self):
        """
        Test that LiveServerTestCase reports a 404 status code when HTTP client
        tries to access a static file that isn't explicitly put under
        STATIC_ROOT.
        """
        try:
            self.urlopen('/static/another_app/another_app_static_file.txt')
        except HTTPError as err:
            self.assertEqual(err.code, 404, 'Expected 404 response')
        else:
            self.fail('Expected 404 response (got %d)' % err.code)

    def test_media_files(self):
        """
        Ensure that the LiveServerTestCase serves media files.
        Refs #2879.
        """
        f = self.urlopen('/media/example_media_file.txt')
        self.assertEqual(f.read().rstrip(b'\r\n'), b'example media file')

    def test_environ(self):
        f = self.urlopen('/environ_view/?%s' % urlencode({'q': 'тест'}))
        self.assertIn(b"QUERY_STRING: 'q=%D1%82%D0%B5%D1%81%D1%82'", f.read())


class LiveServerDatabase(LiveServerBase):

    def test_fixtures_loaded(self):
        """
        Ensure that fixtures are properly loaded and visible to the
        live server thread.
        Refs #2879.
        """
        f = self.urlopen('/model_view/')
        self.assertEqual(f.read().splitlines(), [b'jane', b'robert'])

    def test_database_writes(self):
        """
        Ensure that data written to the database by a view can be read.
        Refs #2879.
        """
        self.urlopen('/create_model_instance/')
        self.assertQuerysetEqual(
            Person.objects.all().order_by('pk'),
            ['jane', 'robert', 'emily'],
            lambda b: b.name
        )
