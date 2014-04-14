# -*- encoding: utf-8 -*-
"""
Tests for django.core.servers.
"""
from __future__ import unicode_literals

from contextlib import contextmanager
import io
import os
import socket
import sys
from unittest import skipIf

from django.core.exceptions import ImproperlyConfigured
from django.test import LiveServerTestCase
from django.test import override_settings
from django.test.utils import patch_logger
from django.utils.http import urlencode
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.request import urlopen
from django.utils._os import upath

from .models import Person


TEST_ROOT = os.path.dirname(upath(__file__))
TEST_SETTINGS = {
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'media'),
    'STATIC_URL': '/static/',
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'static'),
}


@override_settings(ROOT_URLCONF='servers.urls')
class LiveServerBase(LiveServerTestCase):

    available_apps = [
        'servers',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
    ]
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


@contextmanager
def patch_sys_stream(stream_name):
    """
    Context manager that takes "stderr" or "stdout" as a parameter and provides
    a BytesIO containing the output that would have been sent to that sys
    module stream.
    """
    output = six.StringIO()

    orig = getattr(sys, stream_name)
    setattr(sys, stream_name, output)
    try:
        yield output
    finally:
        setattr(sys, stream_name, orig)


class MockHTTPConnection(object):
    """
    Mock HTTPConnection to be used for testing the output of
    QuietWSGIRequestHandler.
    """

    def makefile(self, mode, bufsize):
        return io.BytesIO()


class LiveServerLogging(LiveServerBase):
    """
    Test the effectiveness of QuietWSGIServer and QuietWSGIRequestHandler in
    shifting messages that normally go to stderr and stdout to the logging
    module instead when running a LiveServerTestCase.
    """

    logger_name = "django.request"

    def create_handler_instance(self):
        """
        Create an instance of QuietWSGIRequestHandler to be used for message
        output testing.
        """
        server = self.server_thread.httpd
        handler_class = server.RequestHandlerClass
        request = MockHTTPConnection()
        return handler_class(request, ("test.wsgi.errors", 9999), server)

    def test_handle_error(self):
        """
        Ensure that WSGI error messages are logged instead of being sent to
        stderr and/or stdout when running a LiveServerTestCase.
        Refs #22439.
        """
        server = self.server_thread.httpd
        client_address = "test.handle.error"
        expected = "Exception happened during processing of request from %s" % client_address
        with patch_logger(self.logger_name, "error") as calls:
            with patch_sys_stream("stderr") as stderr:
                with patch_sys_stream("stdout") as stdout:
                    server.handle_error(None, client_address)
                    self.assertEqual(len(stderr.getvalue()), 0)
                    self.assertEqual(len(stdout.getvalue()), 0)
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0], expected)

    def test_wsgi_errors(self):
        """
        Ensure that a unicode message sent to the wsgi.errors stream is logged
        instead of being sent to stderr when running a LiveServerTestCase.
        Refs #22439.
        """
        handler_instance = self.create_handler_instance()
        message = "This should be logged - €1.00"
        output = "%s\n" % message
        with patch_logger(self.logger_name, "error") as calls:
            with patch_sys_stream("stderr") as stderr:
                handler_instance.get_stderr().write(output)
                self.assertEqual(len(stderr.getvalue()), 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0], message)

    @skipIf(sys.version_info[0] > 2, "Python 3 doesn't support writing bytes to stderr")
    def test_wsgi_errors_bytes(self):
        """
        Ensure that a message of bytes sent to the wsgi.errors stream in Python
        2 is logged correctly when running a LiveServerTestCase.
        Refs #22439.
        """
        handler_instance = self.create_handler_instance()
        message = b"This should be logged"
        output = b"%s\n" % message
        with patch_logger(self.logger_name, "error") as calls:
            handler_instance.get_stderr().write(output)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], message)

    def test_wsgi_errors_multiple_lines(self):
        """
        Ensure that a unicode message with multiple lines sent to the
        wsgi.errors stream generates multiple log messages when running a
        LiveServerTestCase.
        Refs #22439.
        """
        handler_instance = self.create_handler_instance()
        first_message = "This should be logged"
        second_message = "on two lines"
        output = "%s\n%s\n" % (first_message, second_message)
        with patch_logger(self.logger_name, "error") as calls:
            handler_instance.get_stderr().write(output)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0], first_message)
            self.assertEqual(calls[1], second_message)

    def test_wsgi_errors_split(self):
        """
        Ensure that unicode messages sent to the wsgi.errors stream in separate
        writes are logged in units separated by the written newlines when
        running a LiveServerTestCase.
        Refs #22439.
        """
        handler_instance = self.create_handler_instance()
        with patch_logger(self.logger_name, "error") as calls:
            stream = handler_instance.get_stderr()
            stream.write("The first ")
            self.assertEqual(len(calls), 0)
            stream.write("line\nThe second")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], "The first line")
            stream.write(" line\n")
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1], "The second line")

    def test_log_message(self):
        """
        Ensure that HTTP status messages are logged instead of being ignored or
        sent to stderr when running a LiveServerTestCase.
        Refs #22439.
        """
        handler_instance = self.create_handler_instance()
        format_string = '"%s" %s %s'
        request_line = "GET /test_log_message/ HTTP/1.1"
        status_code = "200"
        size = "0"
        expected = format_string % (request_line, status_code, size)
        with patch_logger(self.logger_name, "info") as calls:
            with patch_sys_stream("stderr") as stderr:
                handler_instance.log_message(format_string, request_line, status_code, size)
                self.assertEqual(len(stderr.getvalue()), 0)
                self.assertEqual(len(calls), 1)
                # Can't count on being able to accurately predict the exact time
                self.assertRegexpMatches(calls[0], "\[[^\]]+\] %s" % expected)
