"""
A subset of the tests in tests/servers/tests exercising
django.contrib.staticfiles.testing.StaticLiveServerTestCase instead of
django.test.LiveServerTestCase.
"""

import os
from urllib.request import urlopen

from django.test import LiveServerTestCase, modify_settings, override_settings


TEST_ROOT = os.path.dirname(__file__)
TEST_SETTINGS = {
    'DEBUG': True,
    'MEDIA_URL': '/media/',
    'STATIC_URL': '/static/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'media'),
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'static'),
    'INSTALLED_APPS': [
        'django.contrib.whitenoise.runserver_nostatic',
        'django.contrib.staticfiles',

    ],
    'MIDDLEWARE': [
        'django.contrib.whitenoise.middleware.WhiteNoiseMiddleware'
    ],
}


class LiveServerBase(LiveServerTestCase):

    available_apps = []

    @classmethod
    def setUpClass(cls):
        # Override settings
        cls.settings_override = override_settings(**TEST_SETTINGS)
        cls.settings_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Restore original settings
        cls.settings_override.disable()


class StaticLiveServerView(LiveServerBase):

    def urlopen(self, url):
        return urlopen(self.live_server_url + url)

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    def test_collectstatic_emulation(self):
        """
        WhiteNoise and DEBUG=True allow it
        to discover app's static assets without having to collectstatic first.
        """
        with self.urlopen('/static/test/file.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'In static directory.')
