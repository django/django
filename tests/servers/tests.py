"""
Tests for django.core.servers.
"""
import errno
import os
import socket
from http.client import HTTPConnection
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.test import LiveServerTestCase, override_settings

from .models import Person

TEST_ROOT = os.path.dirname(__file__)
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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # put it in a list to prevent descriptor lookups in test
        cls.live_server_url_test = [cls.live_server_url]

    def test_live_server_url_is_class_property(self):
        self.assertIsInstance(self.live_server_url_test[0], str)
        self.assertEqual(self.live_server_url_test[0], self.live_server_url)


class LiveServerViews(LiveServerBase):
    def test_protocol(self):
        """Launched server serves with HTTP 1.1."""
        with self.urlopen('/example_view/') as f:
            self.assertEqual(f.version, 11)

    def test_closes_connection_without_content_length(self):
        """
        A HTTP 1.1 server is supposed to support keep-alive. Since our
        development server is rather simple we support it only in cases where
        we can detect a content length from the response. This should be doable
        for all simple views and streaming responses where an iterable with
        length of one is passed. The latter follows as result of `set_content_length`
        from https://github.com/python/cpython/blob/master/Lib/wsgiref/handlers.py.

        If we cannot detect a content length we explicitly set the `Connection`
        header to `close` to notify the client that we do not actually support
        it.
        """
        conn = HTTPConnection(LiveServerViews.server_thread.host, LiveServerViews.server_thread.port, timeout=1)
        try:
            conn.request('GET', '/streaming_example_view/', headers={'Connection': 'keep-alive'})
            response = conn.getresponse()
            self.assertTrue(response.will_close)
            self.assertEqual(response.read(), b'Iamastream')
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Connection'), 'close')

            conn.request('GET', '/streaming_example_view/', headers={'Connection': 'close'})
            response = conn.getresponse()
            self.assertTrue(response.will_close)
            self.assertEqual(response.read(), b'Iamastream')
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Connection'), 'close')
        finally:
            conn.close()

    def test_keep_alive_on_connection_with_content_length(self):
        """
        See `test_closes_connection_without_content_length` for details. This
        is a follow up test, which ensure that we do not close the connection
        if not needed, hence allowing us to take advantage of keep-alive.
        """
        conn = HTTPConnection(LiveServerViews.server_thread.host, LiveServerViews.server_thread.port)
        try:
            conn.request('GET', '/example_view/', headers={"Connection": "keep-alive"})
            response = conn.getresponse()
            self.assertFalse(response.will_close)
            self.assertEqual(response.read(), b'example view')
            self.assertEqual(response.status, 200)
            self.assertIsNone(response.getheader('Connection'))

            conn.request('GET', '/example_view/', headers={"Connection": "close"})
            response = conn.getresponse()
            self.assertFalse(response.will_close)
            self.assertEqual(response.read(), b'example view')
            self.assertEqual(response.status, 200)
            self.assertIsNone(response.getheader('Connection'))
        finally:
            conn.close()

    def test_keep_alive_connection_clears_previous_request_data(self):
        conn = HTTPConnection(LiveServerViews.server_thread.host, LiveServerViews.server_thread.port)
        try:
            conn.request('POST', '/method_view/', b'{}', headers={"Connection": "keep-alive"})
            response = conn.getresponse()
            self.assertFalse(response.will_close)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b'POST')

            conn.request('POST', '/method_view/', b'{}', headers={"Connection": "close"})
            response = conn.getresponse()
            self.assertFalse(response.will_close)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b'POST')
        finally:
            conn.close()

    def test_404(self):
        with self.assertRaises(HTTPError) as err:
            self.urlopen('/')
        err.exception.close()
        self.assertEqual(err.exception.code, 404, 'Expected 404 response')

    def test_view(self):
        with self.urlopen('/example_view/') as f:
            self.assertEqual(f.read(), b'example view')

    def test_static_files(self):
        with self.urlopen('/static/example_static_file.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'example static file')

    def test_no_collectstatic_emulation(self):
        """
        LiveServerTestCase reports a 404 status code when HTTP client
        tries to access a static file that isn't explicitly put under
        STATIC_ROOT.
        """
        with self.assertRaises(HTTPError) as err:
            self.urlopen('/static/another_app/another_app_static_file.txt')
        err.exception.close()
        self.assertEqual(err.exception.code, 404, 'Expected 404 response')

    def test_media_files(self):
        with self.urlopen('/media/example_media_file.txt') as f:
            self.assertEqual(f.read().rstrip(b'\r\n'), b'example media file')

    def test_environ(self):
        with self.urlopen('/environ_view/?%s' % urlencode({'q': 'тест'})) as f:
            self.assertIn(b"QUERY_STRING: 'q=%D1%82%D0%B5%D1%81%D1%82'", f.read())


class LiveServerDatabase(LiveServerBase):

    def test_fixtures_loaded(self):
        """
        Fixtures are properly loaded and visible to the live server thread.
        """
        with self.urlopen('/model_view/') as f:
            self.assertEqual(f.read().splitlines(), [b'jane', b'robert'])

    def test_database_writes(self):
        """
        Data written to the database by a view can be read.
        """
        with self.urlopen('/create_model_instance/'):
            pass
        self.assertQuerysetEqual(
            Person.objects.all().order_by('pk'),
            ['jane', 'robert', 'emily'],
            lambda b: b.name
        )


class LiveServerPort(LiveServerBase):

    def test_port_bind(self):
        """
        Each LiveServerTestCase binds to a unique port or fails to start a
        server thread when run concurrently (#26011).
        """
        TestCase = type("TestCase", (LiveServerBase,), {})
        try:
            TestCase.setUpClass()
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                # We're out of ports, LiveServerTestCase correctly fails with
                # a socket error.
                return
            # Unexpected error.
            raise
        try:
            # We've acquired a port, ensure our server threads acquired
            # different addresses.
            self.assertNotEqual(
                self.live_server_url, TestCase.live_server_url,
                "Acquired duplicate server addresses for server threads: %s" % self.live_server_url
            )
        finally:
            TestCase.tearDownClass()

    def test_specified_port_bind(self):
        """LiveServerTestCase.port customizes the server's port."""
        TestCase = type(str('TestCase'), (LiveServerBase,), {})
        # Find an open port and tell TestCase to use it.
        s = socket.socket()
        s.bind(('', 0))
        TestCase.port = s.getsockname()[1]
        s.close()
        TestCase.setUpClass()
        try:
            self.assertEqual(
                TestCase.port, TestCase.server_thread.port,
                'Did not use specified port for LiveServerTestCase thread: %s' % TestCase.port
            )
        finally:
            TestCase.tearDownClass()


class LiverServerThreadedTests(LiveServerBase):
    """If LiverServerTestCase isn't threaded, these tests will hang."""

    def test_view_calls_subview(self):
        url = '/subview_calling_view/?%s' % urlencode({'url': self.live_server_url})
        with self.urlopen(url) as f:
            self.assertEqual(f.read(), b'subview calling view: subview')

    def test_check_model_instance_from_subview(self):
        url = '/check_model_instance_from_subview/?%s' % urlencode({
            'url': self.live_server_url,
        })
        with self.urlopen(url) as f:
            self.assertIn(b'emily', f.read())
