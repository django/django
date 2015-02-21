"""
A subset of the tests in tests/servers/tests exercicing
django.contrib.staticfiles.testing.StaticLiveServerTestCase instead of
django.test.LiveServerTestCase.
"""

import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.exceptions import ImproperlyConfigured
from django.test import modify_settings, override_settings
from django.utils._os import upath
from django.utils.six.moves.urllib.request import urlopen

TEST_ROOT = os.path.dirname(upath(__file__))
TEST_SETTINGS = {
    'MEDIA_URL': '/media/',
    'STATIC_URL': '/static/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'media'),
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'static'),
}


class LiveServerBase(StaticLiveServerTestCase):

    available_apps = []

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


class StaticLiveServerChecks(LiveServerBase):

    @classmethod
    def setUpClass(cls):
        # Backup original environment variable
        address_predefined = 'DJANGO_LIVE_TEST_SERVER_ADDRESS' in os.environ
        old_address = os.environ.get('DJANGO_LIVE_TEST_SERVER_ADDRESS')

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
    def tearDownClass(cls):
        # skip it, as setUpClass doesn't call its parent either
        pass

    @classmethod
    def raises_exception(cls, address, exception):
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = address
        try:
            super(StaticLiveServerChecks, cls).setUpClass()
            raise Exception("The line above should have raised an exception")
        except exception:
            pass
        finally:
            super(StaticLiveServerChecks, cls).tearDownClass()

    def test_test_test(self):
        # Intentionally empty method so that the test is picked up by the
        # test runner and the overridden setUpClass() method is executed.
        pass


class StaticLiveServerView(LiveServerBase):

    def urlopen(self, url):
        return urlopen(self.live_server_url + url)

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    def test_collectstatic_emulation(self):
        """
        Test that StaticLiveServerTestCase use of staticfiles' serve() allows it
        to discover app's static assets without having to collectstatic first.
        """
        f = self.urlopen('/static/test/file.txt')
        self.assertEqual(f.read().rstrip(b'\r\n'), b'In static directory.')
