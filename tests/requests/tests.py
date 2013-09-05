# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import time
import warnings
from datetime import datetime, timedelta
from io import BytesIO

from django.db import connection, connections, DEFAULT_DB_ALIAS
from django.core import signals
from django.core.exceptions import SuspiciousOperation
from django.core.handlers.wsgi import WSGIRequest, LimitedStream
from django.http import HttpRequest, HttpResponse, parse_cookie, build_request_repr, UnreadablePostError
from django.test import SimpleTestCase, TransactionTestCase
from django.test.client import FakePayload
from django.test.utils import override_settings, str_prefix
from django.utils import six
from django.utils.unittest import skipIf
from django.utils.http import cookie_date, urlencode
from django.utils.six.moves.urllib.parse import urlencode as original_urlencode
from django.utils.timezone import utc


class RequestsTests(SimpleTestCase):
    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(list(request.GET.keys()), [])
        self.assertEqual(list(request.POST.keys()), [])
        self.assertEqual(list(request.COOKIES.keys()), [])
        self.assertEqual(list(request.META.keys()), [])

    def test_httprequest_repr(self):
        request = HttpRequest()
        request.path = '/somepath/'
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), str_prefix("<HttpRequest\npath:/somepath/,\nGET:{%(_)s'get-key': %(_)s'get-value'},\nPOST:{%(_)s'post-key': %(_)s'post-value'},\nCOOKIES:{%(_)s'post-key': %(_)s'post-value'},\nMETA:{%(_)s'post-key': %(_)s'post-value'}>"))
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={'a': 'b'}, POST_override={'c': 'd'}, COOKIES_override={'e': 'f'}, META_override={'g': 'h'}),
                         str_prefix("<HttpRequest\npath:/otherpath/,\nGET:{%(_)s'a': %(_)s'b'},\nPOST:{%(_)s'c': %(_)s'd'},\nCOOKIES:{%(_)s'e': %(_)s'f'},\nMETA:{%(_)s'g': %(_)s'h'}>"))

    def test_wsgirequest(self):
        request = WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(list(request.GET.keys()), [])
        self.assertEqual(list(request.POST.keys()), [])
        self.assertEqual(list(request.COOKIES.keys()), [])
        self.assertEqual(set(request.META.keys()), set(['PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME', 'wsgi.input']))
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')

    def test_wsgirequest_with_script_name(self):
        """
        Ensure that the request's path is correctly assembled, regardless of
        whether or not the SCRIPT_NAME has a trailing slash.
        Refs #20169.
        """
        # With trailing slash
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'SCRIPT_NAME': '/PREFIX/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(request.path, '/PREFIX/somepath/')
        # Without trailing slash
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'SCRIPT_NAME': '/PREFIX', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(request.path, '/PREFIX/somepath/')

    def test_wsgirequest_with_force_script_name(self):
        """
        Ensure that the FORCE_SCRIPT_NAME setting takes precedence over the
        request's SCRIPT_NAME environment parameter.
        Refs #20169.
        """
        with override_settings(FORCE_SCRIPT_NAME='/FORCED_PREFIX/'):
            request = WSGIRequest({'PATH_INFO': '/somepath/', 'SCRIPT_NAME': '/PREFIX/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
            self.assertEqual(request.path, '/FORCED_PREFIX/somepath/')

    def test_wsgirequest_path_with_force_script_name_trailing_slash(self):
        """
        Ensure that the request's path is correctly assembled, regardless of
        whether or not the FORCE_SCRIPT_NAME setting has a trailing slash.
        Refs #20169.
        """
        # With trailing slash
        with override_settings(FORCE_SCRIPT_NAME='/FORCED_PREFIX/'):
            request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
            self.assertEqual(request.path, '/FORCED_PREFIX/somepath/')
        # Without trailing slash
        with override_settings(FORCE_SCRIPT_NAME='/FORCED_PREFIX'):
            request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
            self.assertEqual(request.path, '/FORCED_PREFIX/somepath/')

    def test_wsgirequest_repr(self):
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), str_prefix("<WSGIRequest\npath:/somepath/,\nGET:{%(_)s'get-key': %(_)s'get-value'},\nPOST:{%(_)s'post-key': %(_)s'post-value'},\nCOOKIES:{%(_)s'post-key': %(_)s'post-value'},\nMETA:{%(_)s'post-key': %(_)s'post-value'}>"))
        self.assertEqual(build_request_repr(request), repr(request))
        self.assertEqual(build_request_repr(request, path_override='/otherpath/', GET_override={'a': 'b'}, POST_override={'c': 'd'}, COOKIES_override={'e': 'f'}, META_override={'g': 'h'}),
                         str_prefix("<WSGIRequest\npath:/otherpath/,\nGET:{%(_)s'a': %(_)s'b'},\nPOST:{%(_)s'c': %(_)s'd'},\nCOOKIES:{%(_)s'e': %(_)s'f'},\nMETA:{%(_)s'g': %(_)s'h'}>"))

    def test_wsgirequest_path_info(self):
        def wsgi_str(path_info):
            path_info = path_info.encode('utf-8')           # Actual URL sent by the browser (bytestring)
            if six.PY3:
                path_info = path_info.decode('iso-8859-1')  # Value in the WSGI environ dict (native string)
            return path_info
        # Regression for #19468
        request = WSGIRequest({'PATH_INFO': wsgi_str("/سلام/"), 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(request.path, "/سلام/")

    def test_parse_cookie(self):
        self.assertEqual(parse_cookie('invalid@key=true'), {})

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


    @override_settings(ALLOWED_HOSTS=[])
    def test_get_host_suggestion_of_allowed_host(self):
        """get_host() makes helpful suggestions if a valid-looking host is not in ALLOWED_HOSTS."""
        msg_invalid_host = "Invalid HTTP_HOST header: %r."
        msg_suggestion = msg_invalid_host + "You may need to add %r to ALLOWED_HOSTS."

        for host in [ # Valid-looking hosts
            'example.com',
            '12.34.56.78',
            '[2001:19f0:feee::dead:beef:cafe]',
            'xn--4ca9at.com', # Punnycode for öäü.com
        ]:
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            self.assertRaisesMessage(
                SuspiciousOperation,
                msg_suggestion % (host, host),
                request.get_host
            )

        for domain, port in [ # Valid-looking hosts with a port number
            ('example.com', 80),
            ('12.34.56.78', 443),
            ('[2001:19f0:feee::dead:beef:cafe]', 8080),
        ]:
            host = '%s:%s' % (domain, port)
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            self.assertRaisesMessage(
                SuspiciousOperation,
                msg_suggestion % (host, domain),
                request.get_host
            )

        for host in [ # Invalid hosts
            'example.com@evil.tld',
            'example.com:dr.frankenstein@evil.tld',
            'example.com:dr.frankenstein@evil.tld:80',
            'example.com:80/badpath',
            'example.com: recovermypassword.com',
        ]:
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            self.assertRaisesMessage(
                SuspiciousOperation,
                msg_invalid_host % host,
                request.get_host
            )


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
        stream = LimitedStream(BytesIO(b'test'), 2)
        self.assertEqual(stream.read(), b'te')
        # Reading again returns nothing.
        self.assertEqual(stream.read(), b'')

        # Read a number of characters greater than the stream has to offer
        stream = LimitedStream(BytesIO(b'test'), 2)
        self.assertEqual(stream.read(5), b'te')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), b'')

        # Read sequentially from a stream
        stream = LimitedStream(BytesIO(b'12345678'), 8)
        self.assertEqual(stream.read(5), b'12345')
        self.assertEqual(stream.read(5), b'678')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(5), b'')

        # Read lines from a stream
        stream = LimitedStream(BytesIO(b'1234\n5678\nabcd\nefgh\nijkl'), 24)
        # Read a full line, unconditionally
        self.assertEqual(stream.readline(), b'1234\n')
        # Read a number of characters less than a line
        self.assertEqual(stream.readline(2), b'56')
        # Read the rest of the partial line
        self.assertEqual(stream.readline(), b'78\n')
        # Read a full line, with a character limit greater than the line length
        self.assertEqual(stream.readline(6), b'abcd\n')
        # Read the next line, deliberately terminated at the line end
        self.assertEqual(stream.readline(4), b'efgh')
        # Read the next line... just the line end
        self.assertEqual(stream.readline(), b'\n')
        # Read everything else.
        self.assertEqual(stream.readline(), b'ijkl')

        # Regression for #15018
        # If a stream contains a newline, but the provided length
        # is less than the number of provided characters, the newline
        # doesn't reset the available character count
        stream = LimitedStream(BytesIO(b'1234\nabcdef'), 9)
        self.assertEqual(stream.readline(10), b'1234\n')
        self.assertEqual(stream.readline(3), b'abc')
        # Now expire the available characters
        self.assertEqual(stream.readline(3), b'd')
        # Reading again returns nothing.
        self.assertEqual(stream.readline(2), b'')

        # Same test, but with read, not readline.
        stream = LimitedStream(BytesIO(b'1234\nabcdef'), 9)
        self.assertEqual(stream.read(6), b'1234\na')
        self.assertEqual(stream.read(2), b'bc')
        self.assertEqual(stream.read(2), b'd')
        self.assertEqual(stream.read(2), b'')
        self.assertEqual(stream.read(), b'')

    def test_stream(self):
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(request.read(), b'name=value')

    def test_read_after_value(self):
        """
        Reading from request is allowed after accessing request contents as
        POST or body.
        """
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(request.POST, {'name': ['value']})
        self.assertEqual(request.body, b'name=value')
        self.assertEqual(request.read(), b'name=value')

    def test_value_after_read(self):
        """
        Construction of POST or body is not allowed after reading
        from request.
        """
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(request.read(2), b'na')
        self.assertRaises(Exception, lambda: request.body)
        self.assertEqual(request.POST, {})

    def test_non_ascii_POST(self):
        payload = FakePayload(urlencode({'key': 'España'}))
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'wsgi.input': payload,
        })
        self.assertEqual(request.POST, {'key': ['España']})

    def test_alternate_charset_POST(self):
        """
        Test a POST with non-utf-8 payload encoding.
        """
        payload = FakePayload(original_urlencode({'key': 'España'.encode('latin-1')}))
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(payload),
            'CONTENT_TYPE': 'application/x-www-form-urlencoded; charset=iso-8859-1',
            'wsgi.input': payload,
        })
        self.assertEqual(request.POST, {'key': ['España']})

    def test_body_after_POST_multipart_form_data(self):
        """
        Reading body after parsing multipart/form-data is not allowed
        """
        # Because multipart is used for large amounts fo data i.e. file uploads,
        # we don't want the data held in memory twice, and we don't want to
        # silence the error by setting body = '' either.
        payload = FakePayload("\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']))
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(request.POST, {'name': ['value']})
        self.assertRaises(Exception, lambda: request.body)

    def test_body_after_POST_multipart_related(self):
        """
        Reading body after parsing multipart that isn't form-data is allowed
        """
        # Ticket #9054
        # There are cases in which the multipart data is related instead of
        # being a binary upload, in which case it should still be accessible
        # via body.
        payload_data = b"\r\n".join([
                b'--boundary',
                b'Content-ID: id; name="name"',
                b'',
                b'value',
                b'--boundary--'
                b''])
        payload = FakePayload(payload_data)
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/related; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(request.POST, {})
        self.assertEqual(request.body, payload_data)

    def test_POST_multipart_with_content_length_zero(self):
        """
        Multipart POST requests with Content-Length >= 0 are valid and need to be handled.
        """
        # According to:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
        # Every request.POST with Content-Length >= 0 is a valid request,
        # this test ensures that we handle Content-Length == 0.
        payload = FakePayload("\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']))
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': 0,
                               'wsgi.input': payload})
        self.assertEqual(request.POST, {})

    def test_POST_binary_only(self):
        payload = b'\r\n\x01\x00\x00\x00ab\x00\x00\xcd\xcc,@'
        environ = {'REQUEST_METHOD': 'POST',
                   'CONTENT_TYPE': 'application/octet-stream',
                   'CONTENT_LENGTH': len(payload),
                   'wsgi.input': BytesIO(payload)}
        request = WSGIRequest(environ)
        self.assertEqual(request.POST, {})
        self.assertEqual(request.FILES, {})
        self.assertEqual(request.body, payload)

        # Same test without specifying content-type
        environ.update({'CONTENT_TYPE': '', 'wsgi.input': BytesIO(payload)})
        request = WSGIRequest(environ)
        self.assertEqual(request.POST, {})
        self.assertEqual(request.FILES, {})
        self.assertEqual(request.body, payload)

    def test_read_by_lines(self):
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        self.assertEqual(list(request), [b'name=value'])

    def test_POST_after_body_read(self):
        """
        POST should be populated even if body is read first
        """
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        raw_data = request.body
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_after_body_read_and_stream_read(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second.
        """
        payload = FakePayload('name=value')
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        raw_data = request.body
        self.assertEqual(request.read(1), b'n')
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_after_body_read_and_stream_read_multipart(self):
        """
        POST should be populated even if body is read first, and then
        the stream is read second. Using multipart/form-data instead of urlencoded.
        """
        payload = FakePayload("\r\n".join([
                '--boundary',
                'Content-Disposition: form-data; name="name"',
                '',
                'value',
                '--boundary--'
                '']))
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': payload})
        raw_data = request.body
        # Consume enough data to mess up the parsing:
        self.assertEqual(request.read(13), b'--boundary\r\nC')
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_connection_error(self):
        """
        If wsgi.input.read() raises an exception while trying to read() the
        POST, the exception should be identifiable (not a generic IOError).
        """
        class ExplodingBytesIO(BytesIO):
            def read(self, len=0):
                raise IOError("kaboom!")

        payload = b'name=value'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': ExplodingBytesIO(payload)})

        with self.assertRaises(UnreadablePostError):
            request.body

    def test_FILES_connection_error(self):
        """
        If wsgi.input.read() raises an exception while trying to read() the
        FILES, the exception should be identifiable (not a generic IOError).
        """
        class ExplodingBytesIO(BytesIO):
            def read(self, len=0):
                raise IOError("kaboom!")

        payload = b'x'
        request = WSGIRequest({'REQUEST_METHOD': 'POST',
                               'CONTENT_TYPE': 'multipart/form-data; boundary=foo_',
                               'CONTENT_LENGTH': len(payload),
                               'wsgi.input': ExplodingBytesIO(payload)})

        with self.assertRaises(UnreadablePostError):
            request.FILES


@skipIf(connection.vendor == 'sqlite'
        and connection.settings_dict['TEST_NAME'] in (None, '', ':memory:'),
        "Cannot establish two connections to an in-memory SQLite database.")
class DatabaseConnectionHandlingTests(TransactionTestCase):

    available_apps = []

    def setUp(self):
        # Use a temporary connection to avoid messing with the main one.
        self._old_default_connection = connections['default']
        del connections['default']

    def tearDown(self):
        try:
            connections['default'].close()
        finally:
            connections['default'] = self._old_default_connection

    def test_request_finished_db_state(self):
        # Force closing connection on request end
        connection.settings_dict['CONN_MAX_AGE'] = 0

        # The GET below will not succeed, but it will give a response with
        # defined ._handler_class. That is needed for sending the
        # request_finished signal.
        response = self.client.get('/')
        # Make sure there is an open connection
        connection.cursor()
        connection.enter_transaction_management()
        signals.request_finished.send(sender=response._handler_class)
        self.assertEqual(len(connection.transaction_state), 0)

    def test_request_finished_failed_connection(self):
        # Force closing connection on request end
        connection.settings_dict['CONN_MAX_AGE'] = 0

        connection.enter_transaction_management()
        connection.set_dirty()
        # Test that the rollback doesn't succeed (for example network failure
        # could cause this).
        def fail_horribly():
            raise Exception("Horrible failure!")
        connection._rollback = fail_horribly
        try:
            with self.assertRaises(Exception):
                signals.request_finished.send(sender=self.__class__)
            # The connection's state wasn't cleaned up
            self.assertEqual(len(connection.transaction_state), 1)
        finally:
            del connection._rollback
        # The connection will be cleaned on next request where the conn
        # works again.
        signals.request_finished.send(sender=self.__class__)
        self.assertEqual(len(connection.transaction_state), 0)
