"""
A subset of the tests in tests/servers/tests exercising
django.contrib.staticfiles.testing.StaticLiveServerTestCase instead of
django.test.LiveServerTestCase.
"""

import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.contrib.staticfiles.handlers import DjangoWhiteNoise
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TestCase, modify_settings, override_settings

TEST_ROOT = os.path.dirname(__file__)
TEST_SETTINGS = {
    'MEDIA_URL': '/media/',
    'STATIC_URL': '/static/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'media'),
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'static'),
}

TEST_SETTINGS_USE_FINDERS = dict(TEST_SETTINGS)
TEST_SETTINGS_USE_FINDERS['WHITENOISE_USE_FINDERS'] = True
TEST_SETTINGS_USE_FINDERS['WHITENOISE_AUTOREFRESH'] = True


@override_settings(**TEST_SETTINGS)
class StaticLiveServerView(StaticLiveServerTestCase):
    available_apps = []

    def urlopen(self, url, *args, **kwargs):
        url = self.live_server_url + url
        request = Request(url, *args, **kwargs)
        return urlopen(request)

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    def test_collectstatic_emulation(self):
        """
        DjangoWhiteNoise and WHITENOISE_USE_FINDERS=False, WHITENOISE_AUTOREFRESH=False disallow it
        to discover app's static assets without having to collectstatic first.
        """
        try:
            self.urlopen('/static/test/file.txt')
        except HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_get_file(self):
        """
        DjangoWhiteNoise serves static files in STATIC_ROOT.
        """
        with self.urlopen('/static/testfile.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'Test!')

    def test_unversioned_file_not_cached_forever(self):
        with self.urlopen('/static/styles.css') as f:
            self.assertEqual(f.headers.get('Cache-Control'),
                             'max-age={}, public'.format(DjangoWhiteNoise.max_age))

    def test_no_content_type_when_not_modified(self):
        last_mod = 'Fri, 11 Apr 2100 11:47:06 GMT'

        try:
            self.urlopen('/static/styles.css', headers={'If-Modified-Since': last_mod})
        except HTTPError as e:
            self.assertEqual(e.code, 304)
            self.assertNotIn('Content-Type', e.headers)

    def test_get_nonascii_file(self):
        with self.urlopen('/static/nonascii%E2%9C%93.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'hi')


@override_settings(**TEST_SETTINGS_USE_FINDERS)
class StaticLiveServerViewUseFinders(StaticLiveServerTestCase):
    available_apps = []

    def urlopen(self, url, *args, **kwargs):
        url = self.live_server_url + url
        request = Request(url, *args, **kwargs)
        return urlopen(request)

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    def test_collectstatic_emulation(self):
        """
        DjangoWhiteNoise and WHITENOISE_USE_FINDERS=True, WHITENOISE_AUTOREFRESH=True allow it
        to discover app's static assets without having to collectstatic first.
        """
        with self.urlopen('/static/test/file.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'In static directory.')

    def test_get_file(self):
        """
        DjangoWhiteNoise serves static files in STATIC_ROOT.
        """
        with self.urlopen('/static/testfile.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'Test!')

    def test_non_ascii_requests_safely_ignored(self):
        try:
            self.urlopen('/%E2%9C%93')
        except HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_requests_for_directory_safely_ignored(self):
        try:
            self.urlopen('/static/test')
        except HTTPError as e:
            self.assertEqual(e.code, 404)


@override_settings(MIDDLEWARE=['django.contrib.staticfiles.middleware.WhiteNoiseMiddleware'])
@override_settings(**TEST_SETTINGS)
class TestWhitenoiseMiddleware(TestCase):

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    def test_collectstatic_emulation(self):
        """
        WHITENOISE_USE_FINDERS=True ignored in WhiteNoiseMiddleware
        """
        response = self.client.get('/static/test/testfile.txt')
        self.assertEqual(response.status_code, 404)

        with self.settings(WHITENOISE_USE_FINDERS=True):
            response = self.client.get('/static/test/testfile.txt')
            self.assertEqual(response.status_code, 404)

    def test_get_file(self):
        """
        WhiteNoiseMiddleware serves static files in STATIC_ROOT.
        """
        response = self.client.get('/static/testfile.txt')
        content = b''
        for item in response.streaming_content:
            content += item
        self.assertEqual(content.rstrip(b'\r\n'), b'Test!')

    def test_unversioned_file_not_cached_forever(self):
        response = self.client.get('/static/styles.css')
        self.assertEqual(response['Cache-Control'], 'max-age={}, public'.format(DjangoWhiteNoise.max_age))

    def test_no_content_type_when_not_modified(self):
        last_mod = 'Fri, 11 Apr 2100 11:47:06 GMT'
        response = self.client.get('/static/styles.css', HTTP_IF_MODIFIED_SINCE=last_mod)
        self.assertEqual(response.status_code, 304)
        self.assertRaises(KeyError, response.__getitem__, 'Content-Type')

    def test_get_nonascii_file(self):
        response = self.client.get('/static/nonascii%E2%9C%93.txt')
        content = b''
        for item in response.streaming_content:
            content += item
        self.assertEqual(content.rstrip(b'\r\n'), b'hi')
