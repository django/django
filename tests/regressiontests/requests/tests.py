# -*- coding: utf-8 -*-
from __future__ import with_statement

import time
import warnings
from datetime import datetime, timedelta
from StringIO import StringIO

from django.db import connection, connections, DEFAULT_DB_ALIAS
from django.core import signals
from django.conf import settings
from django.core.handlers.modpython import ModPythonRequest
from django.core.exceptions import SuspiciousOperation
from django.core.handlers.wsgi import WSGIRequest, LimitedStream
from django.http import HttpRequest, HttpResponse, parse_cookie, build_request_repr, UnreadablePostError
from django.test import TransactionTestCase
from django.test.utils import get_warnings_state, restore_warnings_state, override_settings
from django.utils import unittest
from django.utils.http import cookie_date
from django.utils.timezone import utc


class RequestsTests(unittest.TestCase):
    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_httprequest_repr(self):
        request = HttpRequest()
        request.path = u'/somepath/'
        request.GET = {u'get-key': u'get-value'}
        request.POST = {u'post-key': u'post-value'}
        request.COOKIES = {u'post-key': u'post-value'}
        request.META = {u'post-key': u'post-value'}
        self.assertEqual(repr(request), u"<HttpRequest\npath:/somepath/,\nGET:{u'get-key': u'get-value'},\nPOST:{u'post-key': u'post-value'},\nCOOKIES:{u'post-key': u'post-value'},\nMETA:{u'post-key': u'post-value'}>")
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={u'a': u'b'}, POST_override={u'c': u'd'}, COOKIES_override={u'e': u'f'}, META_override={u'g': u'h'}),
                         u"<HttpRequest\npath:/otherpath/,\nGET:{u'a': u'b'},\nPOST:{u'c': u'd'},\nCOOKIES:{u'e': u'f'},\nMETA:{u'g': u'h'}>")

    def test_wsgirequest(self):
        request = WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus', 'wsgi.input': StringIO('')})
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(set(request.META.keys()), set(['PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME', 'wsgi.input']))
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')

    def test_wsgirequest_repr(self):
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': StringIO('')})
        request.GET = {u'get-key': u'get-value'}
        request.POST = {u'post-key': u'post-value'}
        request.COOKIES = {u'post-key': u'post-value'}
        request.META = {u'post-key': u'post-value'}
        self.assertEqual(repr(request), u"<WSGIRequest\npath:/somepath/,\nGET:{u'get-key': u'get-value'},\nPOST:{u'post-key': u'post-value'},\nCOOKIES:{u'post-key': u'post-value'},\nMETA:{u'post-key': u'post-value'}>")
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={u'a': u'b'}, POST_override={u'c': u'd'}, COOKIES_override={u'e': u'f'}, META_override={u'g': u'h'}),
                         u"<WSGIRequest\npath:/otherpath/,\nGET:{u'a': u'b'},\nPOST:{u'c': u'd'},\nCOOKIES:{u'e': u'f'},\nMETA:{u'g': u'h'}>")

    def test_modpythonrequest(self):
        class FakeModPythonRequest(ModPythonRequest):
           def __init__(self, *args, **kwargs):
               super(FakeModPythonRequest, self).__init__(*args, **kwargs)
               self._get = self._post = self._meta = self._cookies = {}

        class Dummy:
            def get_options(self):
                return {}

        req = Dummy()
        req.uri = 'bogus'
        request = FakeModPythonRequest(req)
        self.assertEqual(request.path, 'bogus')
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_modpythonrequest_repr(self):
        class Dummy:
            def get_options(self):
                return {}
        req = Dummy()
        req.uri = '/somepath/'
        request = ModPythonRequest(req)
        request._get = {u'get-key': u'get-value'}
        request._post = {u'post-key': u'post-value'}
        request._cookies = {u'post-key': u'post-value'}
        request._meta = {u'post-key': u'post-value'}
        self.assertEqual(repr(request), u"<ModPythonRequest\npath:/somepath/,\nGET:{u'get-key': u'get-value'},\nPOST:{u'post-key': u'post-value'},\nCOOKIES:{u'post-key': u'post-value'},\nMETA:{u'post-key': u'post-value'}>")
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={u'a': u'b'}, POST_override={u'c': u'd'}, COOKIES_override={u'e': u'f'}, META_override={u'g': u'h'}),
                         u"<ModPythonRequest\npath:/otherpath/,\nGET:{u'a': u'b'},\nPOST:{u'c': u'd'},\nCOOKIES:{u'e': u'f'},\nMETA:{u'g': u'h'}>")

    def test_parse_cookie(self):
        self.assertEqual(parse_cookie('invalid:key=true'), {})

    def test_httprequest_location(self):
        request = HttpRequest()
        self.assertEqual(request.build_absolute_uri(location="https://www.example.com/asdf"),
            'https://www.example.com/asdf')

        request.get_host = lambda: 'www.example.com'
        request.path = ''
        self.assertEqual(request.build_absolute_uri(location="/path/with:colons"),
            'http://www.example.com/path/with:colons')

    @override_settings(
        USE_X_FORWARDED_HOST=False,
        ALLOWED_HOSTS=[
            'forward.com', 'example.com', 'internal.com', '12.34.56.78',
            '[2001:19f0:feee::dead:beef:cafe]', 'xn--4ca9at.com',
            '.multitenant.com', 'INSENSITIVE.com',
            ])
    def test_http_get_host(self):
        # Check if X_FORWARDED_HOST is provided.
        request = HttpRequest()
        request.META = {
            'HTTP_X_FORWARDED_HOST': 'forward.com',
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        # X_FORWARDED_HOST is ignored.
        self.assertEqual(request.get_host(), 'example.com')

        # Check if X_FORWARDED_HOST isn't provided.
        request = HttpRequest()
        request.META = {
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        self.assertEqual(request.get_host(), 'example.com')

        # Check if HTTP_HOST isn't provided.
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        self.assertEqual(request.get_host(), 'internal.com')

        # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 8042,
        }
        self.assertEqual(request.get_host(), 'internal.com:8042')

        # Poisoned host headers are rejected as suspicious
        legit_hosts = [
            'example.com',
            'example.com:80',
            '12.34.56.78',
            '12.34.56.78:443',
            '[2001:19f0:feee::dead:beef:cafe]',
            '[2001:19f0:feee::dead:beef:cafe]:8080',
            'xn--4ca9at.com', # Punnycode for öäü.com
            'anything.multitenant.com',
            'multitenant.com',
            'insensitive.com',
        ]

        poisoned_hosts = [
            'example.com@evil.tld',
            'example.com:dr.frankenstein@evil.tld',
            'example.com:dr.frankenstein@evil.tld:80',
            'example.com:80/badpath',
            'example.com: recovermypassword.com',
            'other.com', # not in ALLOWED_HOSTS
        ]

        for host in legit_hosts:
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': host,
            }
            request.get_host()

        for host in poisoned_hosts:
            with self.assertRaises(SuspiciousOperation):
                request = HttpRequest()
                request.META = {
                    'HTTP_HOST': host,
                }
                request.get_host()

    @override_settings(USE_X_FORWARDED_HOST=True, ALLOWED_HOSTS=['*'])
    def test_http_get_host_with_x_forwarded_host(self):
        # Check if X_FORWARDED_HOST is provided.
        request = HttpRequest()
        request.META = {
            'HTTP_X_FORWARDED_HOST': 'forward.com',
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        # X_FORWARDED_HOST is obeyed.
        self.assertEqual(request.get_host(), 'forward.com')

        # Check if X_FORWARDED_HOST isn't provided.
        request = HttpRequest()
        request.META = {
            'HTTP_HOST': 'example.com',
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        self.assertEqual(request.get_host(), 'example.com')

        # Check if HTTP_HOST isn't provided.
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 80,
        }
        self.assertEqual(request.get_host(), 'internal.com')

        # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'internal.com',
            'SERVER_PORT': 8042,
        }
        self.assertEqual(request.get_host(), 'internal.com:8042')

        # Poisoned host headers are rejected as suspicious
        legit_hosts = [
            'example.com',
            'example.com:80',
            '12.34.56.78',
            '12.34.56.78:443',
            '[2001:19f0:feee::dead:beef:cafe]',
            '[2001:19f0:feee::dead:beef:cafe]:8080',
            'xn--4ca9at.com', # Punnycode for öäü.com
        ]

        poisoned_hosts = [
            'example.com@evil.tld',
            'example.com:dr.frankenstein@evil.tld',
            'example.com:dr.frankenstein@evil.tld:80',
            'example.com:80/badpath',
            'example.com: recovermypassword.com',
        ]

        for host in legit_hosts:
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': host,
            }
            request.get_host()

        for host in poisoned_hosts:
            with self.assertRaises(SuspiciousOperation):
                request = HttpRequest()
                request.META = {
                    'HTTP_HOST': host,
                }
                request.get_host()

    @override_settings(DEBUG=True, ALLOWED_HOSTS=[])
    def test_host_validation_disabled_in_debug_mode(self):
        """If ALLOWED_HOSTS is empty and DEBUG is True, all hosts pass."""
        request = HttpRequest()
        request.META = {
            'HTTP_HOST': 'example.com',
        }
        self.assertEqual(request.get_host(), 'example.com')

    def test_near_expiration(self):
        "Cookie will expire when an near expiration time is provided"
        response = HttpResponse()
        # There is a timing weakness in this test; The
        # expected result for max-age requires that there be
        # a very slight difference between the evaluated expiration
        # time, and the time evaluated in set_cookie(). If this
        # difference doesn't exist, the cookie time will be
        # 1 second larger. To avoid the problem, put in a quick sleep,
        # which guarantees that there will be a time difference.
        expires = datetime.utcnow() + timedelta(seconds=10)
        time.sleep(0.001)
        response.set_cookie('datetime', expires=expires)
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['max-age'], 10)

    def test_aware_expiration(self):
        "Cookie accepts an aware datetime as expiration time"
        response = HttpResponse()
        expires = (datetime.utcnow() + timedelta(seconds=10)).replace(tzinfo=utc)
        time.sleep(0.001)
        response.set_cookie('datetime', expires=expires)
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['max-age'], 10)

    def test_far_expiration(self):
        "Cookie will expire when an distant expiration time is provided"
        response = HttpResponse()
        response.set_cookie('datetime', expires=datetime(2028, 1, 1, 4, 5, 6))
        datetime_cookie = response.cookies['datetime']
        self.assertEqual(datetime_cookie['expires'], 'Sat, 01-Jan-2028 04:05:06 GMT')

    def test_max_age_expiration(self):
        "Cookie will expire if max_age is provided"
        response = HttpResponse()
        response.set_cookie('max_age', max_age=10)
        max_age_cookie = response.cookies['max_age']
        self.assertEqual(max_age_cookie['max-age'], 10)
        self.assertEqual(max_age_cookie['expires'], cookie_date(time.time()+10))

    def test_httponly_cookie(self):
        response = HttpResponse()
        response.set_cookie('example', httponly=True)
        example_cookie = response.cookies['example']
        # A compat cookie may be in use -- check that it has worked
        # both as an output string, and using the cookie attributes
        self.assertTrue('; httponly' in str(example_cookie))
        self.assertTrue(example_cookie['httponly'])

    def test_limited_stream(self):
        # Read all of a limited stream
        stream = LimitedStream(StringIO('test'), 2)
        self.assertEqual(stream.read(), 'te')
        # Reading again returns nothing.
        self.assertEqual(stream.read(), '')

        # Read a number of characters greater than the stream has to offer
        stream = LimitedStream(StringIO('test'), 2)
        self.assertEqual(stream.read(5), 'te')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), '')

        # Read sequentially from a stream
        stream = LimitedStream(StringIO('12345678'), 8)
        self.assertEqual(stream.read(5), '12345')
        self.assertEqual(stream.read(5), '678')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), '')

        # Read lines from a stream
        stream = LimitedStream(StringIO('1234\n5678\nabcd\nefgh\nijkl'), 24)
        # Read a full line, unconditionally
        self.assertEqual(stream.readline(), '1234\n')
        # Read a number of characters less than a line
        self.assertEqual(stream.readline(2), '56')
        # Read the rest of the partial line
        self.assertEqual(stream.readline(), '78\n')
        # Read a full line, with a character limit greater than the line length
        self.assertEqual(stream.readline(6), 'abcd\n')
        # Read the next line, deliberately terminated at the line end
        self.assertEqual(stream.readline(4), 'efgh')
        # Read the next line... just the line end
        self.assertEqual(stream.readline(), '\n')
        # Read everything else.
        self.assertEqual(stream.readline(), 'ijkl')

        # Regression for #15018
        # If a stream contains a newline, but the provided length
        # is less than the number of provided characters, the newline
        # doesn't reset the available character count
        stream = LimitedStream(StringIO('1234\nabcdef'), 9)
        self.assertEqual(stream.readline(10), '1234\n')
        self.assertEqual(stream.readline(3), 'abc')
        # Now expire the available characters
        self.assertEqual(stream.readline(3), 'd')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(2), '')

        # Same test, but with read, not readline.
        stream = LimitedStream(StringIO('1234\nabcdef'), 9)
        self.assertEqual(stream.read(6), '1234\na')
        self.assertEqual(stream.read(2), 'bc')
        self.assertEqual(stream.read(2), 'd')
        self.assertEqual(stream.read(2), '')
        self.assertEqual(stream.read(), '')

    def test_stream(self):
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.read(), 'name=value')

    def test_read_after_value(self):
        """
        Reading from request is allowed after accessing request contents as
        POST or body.
        """
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {u'name': [u'value']})
        self.assertEqual(request.body, 'name=value')
        self.assertEqual(request.read(), 'name=value')

    def test_value_after_read(self):
        """
        Construction of POST or body is not allowed after reading
        from request.
        """
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.read(2), 'na')
        self.assertRaises(Exception, lambda: request.body)
        self.assertEqual(request.POST, {})

    def test_body_after_POST_multipart(self):
        """
        Reading body after parsing multipart is not allowed
        """
        # Because multipart is used for large amounts fo data i.e. file uploads,
        # we don't want the data held in memory twice, and we don't want to
        # silence the error by setting body = '' either.
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                ''])
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {u'name': [u'value']})
        self.assertRaises(Exception, lambda: request.body)

    def test_POST_multipart_with_content_length_zero(self):
        """
        Multipart POST requests with Content-Length >= 0 are valid and need to be handled.
        """
        # According to:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
        # Every request.POST with Content-Length >= 0 is a valid request,
        # this test ensures that we handle Content-Length == 0.
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                ''])
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': 0,
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(request.POST, {})

    def test_read_by_lines(self):
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        self.assertEqual(list(request), ['name=value'])

    def test_POST_after_body_read(self):
        """
        POST should be populated even if body is read first
        """
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        self.assertEqual(request.POST, {u'name': [u'value']})

    def test_POST_after_body_read_and_stream_read(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second.
        """
        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        self.assertEqual(request.read(1), u'n')
        self.assertEqual(request.POST, {u'name': [u'value']})

    def test_POST_after_body_read_and_stream_read_multipart(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second. Using multipart/form-data instead of urlencoded.
        """
        payload = "\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                ''])
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': StringIO(payload)})
        raw_data = request.body
        # Consume enough data to mess up the parsing:
        self.assertEqual(request.read(13), u'--boundary\r\nC')
        self.assertEqual(request.POST, {u'name': [u'value']})

    def test_raw_post_data_returns_body(self):
        """
        HttpRequest.raw_post_body should be the same as HttpRequest.body
        """
        payload = 'Hello There!'
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(payload),
            'wsgi.input': StringIO(payload)
        })

        warnings_state = get_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning, module='django.http')
        try:
            self.assertEqual(request.body, request.raw_post_data)
        finally:
            restore_warnings_state(warnings_state)


    def test_POST_connection_error(self):
        """
        If wsgi.input.read() raises an exception while trying to read() the
        POST, the exception should be identifiable (not a generic IOError).
        """
        class ExplodingStringIO(StringIO):
            def read(self, len=0):
                raise IOError("kaboom!")

        payload = 'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': ExplodingStringIO(payload)})

        with self.assertRaises(UnreadablePostError):
            request.raw_post_data

class TransactionRequestTests(TransactionTestCase):
    def test_request_finished_db_state(self):
        # Make sure there is an open connection
        connection.cursor()
        connection.enter_transaction_management()
        connection.managed(True)
        signals.request_finished.send(sender=self.__class__)
        # In-memory sqlite doesn't actually close connections.
        if connection.vendor != 'sqlite':
            self.assertIs(connection.connection, None)
        self.assertEqual(len(connection.transaction_state), 0)

    @unittest.skipIf(connection.vendor == 'sqlite',
                     'This test will close the connection, in-memory '
                     'sqlite connections must not be closed.')
    def test_request_finished_failed_connection(self):
        conn = connections[DEFAULT_DB_ALIAS]
        conn.enter_transaction_management()
        conn.managed(True)
        conn.set_dirty()
        # Test that the rollback doesn't succeed (for example network failure
        # could cause this).
        def fail_horribly():
            raise Exception("Horrible failure!")
        conn._rollback = fail_horribly
        try:
            with self.assertRaises(Exception):
                signals.request_finished.send(sender=self.__class__)
            # The connection's state wasn't cleaned up
            self.assertTrue(len(connection.transaction_state), 1)
        finally:
            del conn._rollback
        # The connection will be cleaned on next request where the conn
        # works again.
        signals.request_finished.send(sender=self.__class__)
        self.assertEqual(len(connection.transaction_state), 0)
