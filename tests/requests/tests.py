import time
from datetime import datetime, timedelta
from http import cookies
from io import BytesIO
from itertools import chain
from urllib.parse import urlencode

from django.core.exceptions import SuspiciousOperation
from django.core.handlers.wsgi import LimitedStream, WSGIRequest
from django.http import (
    HttpRequest, HttpResponse, RawPostDataException, UnreadablePostError,
)
from django.http.request import split_domain_port
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.client import FakePayload
from django.test.utils import freeze_time
from django.utils.http import cookie_date
from django.utils.timezone import utc


class RequestsTests(SimpleTestCase):
    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(list(request.GET.keys()), [])
        self.assertEqual(list(request.POST.keys()), [])
        self.assertEqual(list(request.COOKIES.keys()), [])
        self.assertEqual(list(request.META.keys()), [])

        # .GET and .POST should be QueryDicts
        self.assertEqual(request.GET.urlencode(), '')
        self.assertEqual(request.POST.urlencode(), '')

        # and FILES should be MultiValueDict
        self.assertEqual(request.FILES.getlist('foo'), [])

        self.assertIsNone(request.content_type)
        self.assertIsNone(request.content_params)

    def test_httprequest_full_path(self):
        request = HttpRequest()
        request.path = request.path_info = '/;some/?awful/=path/foo:bar/'
        request.META['QUERY_STRING'] = ';some=query&+query=string'
        expected = '/%3Bsome/%3Fawful/%3Dpath/foo:bar/?;some=query&+query=string'
        self.assertEqual(request.get_full_path(), expected)

    def test_httprequest_full_path_with_query_string_and_fragment(self):
        request = HttpRequest()
        request.path = request.path_info = '/foo#bar'
        request.META['QUERY_STRING'] = 'baz#quux'
        self.assertEqual(request.get_full_path(), '/foo%23bar?baz#quux')

    def test_httprequest_repr(self):
        request = HttpRequest()
        request.path = '/somepath/'
        request.method = 'GET'
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), "<HttpRequest: GET '/somepath/'>")

    def test_httprequest_repr_invalid_method_and_path(self):
        request = HttpRequest()
        self.assertEqual(repr(request), "<HttpRequest>")
        request = HttpRequest()
        request.method = "GET"
        self.assertEqual(repr(request), "<HttpRequest>")
        request = HttpRequest()
        request.path = ""
        self.assertEqual(repr(request), "<HttpRequest>")

    def test_wsgirequest(self):
        request = WSGIRequest({
            'PATH_INFO': 'bogus',
            'REQUEST_METHOD': 'bogus',
            'CONTENT_TYPE': 'text/html; charset=utf8',
            'wsgi.input': BytesIO(b''),
        })
        self.assertEqual(list(request.GET.keys()), [])
        self.assertEqual(list(request.POST.keys()), [])
        self.assertEqual(list(request.COOKIES.keys()), [])
        self.assertEqual(
            set(request.META.keys()),
            {'PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME', 'CONTENT_TYPE', 'wsgi.input'}
        )
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')
        self.assertEqual(request.content_type, 'text/html')
        self.assertEqual(request.content_params, {'charset': 'utf8'})

    def test_wsgirequest_with_script_name(self):
        """
        The request's path is correctly assembled, regardless of whether or
        not the SCRIPT_NAME has a trailing slash (#20169).
        """
        # With trailing slash
        request = WSGIRequest({
            'PATH_INFO': '/somepath/',
            'SCRIPT_NAME': '/PREFIX/',
            'REQUEST_METHOD': 'get',
            'wsgi.input': BytesIO(b''),
        })
        self.assertEqual(request.path, '/PREFIX/somepath/')
        # Without trailing slash
        request = WSGIRequest({
            'PATH_INFO': '/somepath/',
            'SCRIPT_NAME': '/PREFIX',
            'REQUEST_METHOD': 'get',
            'wsgi.input': BytesIO(b''),
        })
        self.assertEqual(request.path, '/PREFIX/somepath/')

    def test_wsgirequest_script_url_double_slashes(self):
        """
        WSGI squashes multiple successive slashes in PATH_INFO, WSGIRequest
        should take that into account when populating request.path and
        request.META['SCRIPT_NAME'] (#17133).
        """
        request = WSGIRequest({
            'SCRIPT_URL': '/mst/milestones//accounts/login//help',
            'PATH_INFO': '/milestones/accounts/login/help',
            'REQUEST_METHOD': 'get',
            'wsgi.input': BytesIO(b''),
        })
        self.assertEqual(request.path, '/mst/milestones/accounts/login/help')
        self.assertEqual(request.META['SCRIPT_NAME'], '/mst')

    def test_wsgirequest_with_force_script_name(self):
        """
        The FORCE_SCRIPT_NAME setting takes precedence over the request's
        SCRIPT_NAME environment parameter (#20169).
        """
        with override_settings(FORCE_SCRIPT_NAME='/FORCED_PREFIX/'):
            request = WSGIRequest({
                'PATH_INFO': '/somepath/',
                'SCRIPT_NAME': '/PREFIX/',
                'REQUEST_METHOD': 'get',
                'wsgi.input': BytesIO(b''),
            })
            self.assertEqual(request.path, '/FORCED_PREFIX/somepath/')

    def test_wsgirequest_path_with_force_script_name_trailing_slash(self):
        """
        The request's path is correctly assembled, regardless of whether or not
        the FORCE_SCRIPT_NAME setting has a trailing slash (#20169).
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
        request = WSGIRequest({'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(repr(request), "<WSGIRequest: GET '/'>")
        request = WSGIRequest({'PATH_INFO': '/somepath/', 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        request.GET = {'get-key': 'get-value'}
        request.POST = {'post-key': 'post-value'}
        request.COOKIES = {'post-key': 'post-value'}
        request.META = {'post-key': 'post-value'}
        self.assertEqual(repr(request), "<WSGIRequest: GET '/somepath/'>")

    def test_wsgirequest_path_info(self):
        def wsgi_str(path_info, encoding='utf-8'):
            path_info = path_info.encode(encoding)  # Actual URL sent by the browser (bytestring)
            path_info = path_info.decode('iso-8859-1')  # Value in the WSGI environ dict (native string)
            return path_info
        # Regression for #19468
        request = WSGIRequest({'PATH_INFO': wsgi_str("/سلام/"), 'REQUEST_METHOD': 'get', 'wsgi.input': BytesIO(b'')})
        self.assertEqual(request.path, "/سلام/")

        # The URL may be incorrectly encoded in a non-UTF-8 encoding (#26971)
        request = WSGIRequest({
            'PATH_INFO': wsgi_str("/café/", encoding='iso-8859-1'),
            'REQUEST_METHOD': 'get',
            'wsgi.input': BytesIO(b''),
        })
        # Since it's impossible to decide the (wrong) encoding of the URL, it's
        # left percent-encoded in the path.
        self.assertEqual(request.path, "/caf%E9/")

    def test_httprequest_location(self):
        request = HttpRequest()
        self.assertEqual(
            request.build_absolute_uri(location="https://www.example.com/asdf"),
            'https://www.example.com/asdf'
        )

        request.get_host = lambda: 'www.example.com'
        request.path = ''
        self.assertEqual(
            request.build_absolute_uri(location="/path/with:colons"),
            'http://www.example.com/path/with:colons'
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

    def test_create_cookie_after_deleting_cookie(self):
        """
        Setting a cookie after deletion should clear the expiry date.
        """
        response = HttpResponse()
        response.set_cookie('c', 'old-value')
        self.assertEqual(response.cookies['c']['expires'], '')
        response.delete_cookie('c')
        self.assertEqual(response.cookies['c']['expires'], 'Thu, 01-Jan-1970 00:00:00 GMT')
        response.set_cookie('c', 'new-value')
        self.assertEqual(response.cookies['c']['expires'], '')

    def test_far_expiration(self):
        "Cookie will expire when an distant expiration time is provided"
        response = HttpResponse()
        response.set_cookie('datetime', expires=datetime(2028, 1, 1, 4, 5, 6))
        datetime_cookie = response.cookies['datetime']
        self.assertIn(
            datetime_cookie['expires'],
            # assertIn accounts for slight time dependency (#23450)
            ('Sat, 01-Jan-2028 04:05:06 GMT', 'Sat, 01-Jan-2028 04:05:07 GMT')
        )

    def test_max_age_expiration(self):
        "Cookie will expire if max_age is provided"
        response = HttpResponse()
        set_cookie_time = time.time()
        with freeze_time(set_cookie_time):
            response.set_cookie('max_age', max_age=10)
        max_age_cookie = response.cookies['max_age']
        self.assertEqual(max_age_cookie['max-age'], 10)
        self.assertEqual(max_age_cookie['expires'], cookie_date(set_cookie_time + 10))

    def test_httponly_cookie(self):
        response = HttpResponse()
        response.set_cookie('example', httponly=True)
        example_cookie = response.cookies['example']
        # A compat cookie may be in use -- check that it has worked
        # both as an output string, and using the cookie attributes
        self.assertIn('; %s' % cookies.Morsel._reserved['httponly'], str(example_cookie))
        self.assertTrue(example_cookie['httponly'])

    def test_unicode_cookie(self):
        "Verify HttpResponse.set_cookie() works with unicode data."
        response = HttpResponse()
        cookie_value = '清風'
        response.set_cookie('test', cookie_value)
        self.assertEqual(cookie_value, response.cookies['test'].value)

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
        with self.assertRaises(RawPostDataException):
            request.body
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
        payload = FakePayload(urlencode({'key': 'España'.encode('latin-1')}))
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
        # Because multipart is used for large amounts of data i.e. file uploads,
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
        with self.assertRaises(RawPostDataException):
            request.body

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
        request.body  # evaluate
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
        request.body  # evaluate
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
        request.body  # evaluate
        # Consume enough data to mess up the parsing:
        self.assertEqual(request.read(13), b'--boundary\r\nC')
        self.assertEqual(request.POST, {'name': ['value']})

    def test_POST_immutable_for_mutipart(self):
        """
        MultiPartParser.parse() leaves request.POST immutable.
        """
        payload = FakePayload("\r\n".join([
            '--boundary',
            'Content-Disposition: form-data; name="name"',
            '',
            'value',
            '--boundary--',
        ]))
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'multipart/form-data; boundary=boundary',
            'CONTENT_LENGTH': len(payload),
            'wsgi.input': payload,
        })
        self.assertFalse(request.POST._mutable)

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

    def test_set_encoding_clears_POST(self):
        payload = FakePayload('name=Hello Günter')
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': len(payload),
            'wsgi.input': payload,
        })
        self.assertEqual(request.POST, {'name': ['Hello Günter']})
        request.encoding = 'iso-8859-16'
        self.assertEqual(request.POST, {'name': ['Hello GĂŒnter']})

    def test_set_encoding_clears_GET(self):
        request = WSGIRequest({
            'REQUEST_METHOD': 'GET',
            'wsgi.input': '',
            'QUERY_STRING': 'name=Hello%20G%C3%BCnter',
        })
        self.assertEqual(request.GET, {'name': ['Hello Günter']})
        request.encoding = 'iso-8859-16'
        self.assertEqual(request.GET, {'name': ['Hello G\u0102\u0152nter']})

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

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_get_raw_uri(self):
        factory = RequestFactory(HTTP_HOST='evil.com')
        request = factory.get('////absolute-uri')
        self.assertEqual(request.get_raw_uri(), 'http://evil.com//absolute-uri')

        request = factory.get('/?foo=bar')
        self.assertEqual(request.get_raw_uri(), 'http://evil.com/?foo=bar')

        request = factory.get('/path/with:colons')
        self.assertEqual(request.get_raw_uri(), 'http://evil.com/path/with:colons')


class HostValidationTests(SimpleTestCase):
    poisoned_hosts = [
        'example.com@evil.tld',
        'example.com:dr.frankenstein@evil.tld',
        'example.com:dr.frankenstein@evil.tld:80',
        'example.com:80/badpath',
        'example.com: recovermypassword.com',
    ]

    @override_settings(
        USE_X_FORWARDED_HOST=False,
        ALLOWED_HOSTS=[
            'forward.com', 'example.com', 'internal.com', '12.34.56.78',
            '[2001:19f0:feee::dead:beef:cafe]', 'xn--4ca9at.com',
            '.multitenant.com', 'INSENSITIVE.com', '[::ffff:169.254.169.254]',
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

        legit_hosts = [
            'example.com',
            'example.com:80',
            '12.34.56.78',
            '12.34.56.78:443',
            '[2001:19f0:feee::dead:beef:cafe]',
            '[2001:19f0:feee::dead:beef:cafe]:8080',
            'xn--4ca9at.com',  # Punycode for öäü.com
            'anything.multitenant.com',
            'multitenant.com',
            'insensitive.com',
            'example.com.',
            'example.com.:80',
            '[::ffff:169.254.169.254]',
        ]

        for host in legit_hosts:
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': host,
            }
            request.get_host()

        # Poisoned host headers are rejected as suspicious
        for host in chain(self.poisoned_hosts, ['other.com', 'example.com..']):
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
            'xn--4ca9at.com',  # Punycode for öäü.com
        ]

        for host in legit_hosts:
            request = HttpRequest()
            request.META = {
                'HTTP_HOST': host,
            }
            request.get_host()

        for host in self.poisoned_hosts:
            with self.assertRaises(SuspiciousOperation):
                request = HttpRequest()
                request.META = {
                    'HTTP_HOST': host,
                }
                request.get_host()

    @override_settings(USE_X_FORWARDED_PORT=False)
    def test_get_port(self):
        request = HttpRequest()
        request.META = {
            'SERVER_PORT': '8080',
            'HTTP_X_FORWARDED_PORT': '80',
        }
        # Shouldn't use the X-Forwarded-Port header
        self.assertEqual(request.get_port(), '8080')

        request = HttpRequest()
        request.META = {
            'SERVER_PORT': '8080',
        }
        self.assertEqual(request.get_port(), '8080')

    @override_settings(USE_X_FORWARDED_PORT=True)
    def test_get_port_with_x_forwarded_port(self):
        request = HttpRequest()
        request.META = {
            'SERVER_PORT': '8080',
            'HTTP_X_FORWARDED_PORT': '80',
        }
        # Should use the X-Forwarded-Port header
        self.assertEqual(request.get_port(), '80')

        request = HttpRequest()
        request.META = {
            'SERVER_PORT': '8080',
        }
        self.assertEqual(request.get_port(), '8080')

    @override_settings(DEBUG=True, ALLOWED_HOSTS=[])
    def test_host_validation_in_debug_mode(self):
        """
        If ALLOWED_HOSTS is empty and DEBUG is True, variants of localhost are
        allowed.
        """
        valid_hosts = ['localhost', '127.0.0.1', '[::1]']
        for host in valid_hosts:
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            self.assertEqual(request.get_host(), host)

        # Other hostnames raise a SuspiciousOperation.
        with self.assertRaises(SuspiciousOperation):
            request = HttpRequest()
            request.META = {'HTTP_HOST': 'example.com'}
            request.get_host()

    @override_settings(ALLOWED_HOSTS=[])
    def test_get_host_suggestion_of_allowed_host(self):
        """get_host() makes helpful suggestions if a valid-looking host is not in ALLOWED_HOSTS."""
        msg_invalid_host = "Invalid HTTP_HOST header: %r."
        msg_suggestion = msg_invalid_host + " You may need to add %r to ALLOWED_HOSTS."
        msg_suggestion2 = msg_invalid_host + " The domain name provided is not valid according to RFC 1034/1035"

        for host in [  # Valid-looking hosts
            'example.com',
            '12.34.56.78',
            '[2001:19f0:feee::dead:beef:cafe]',
            'xn--4ca9at.com',  # Punycode for öäü.com
        ]:
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            with self.assertRaisesMessage(SuspiciousOperation, msg_suggestion % (host, host)):
                request.get_host()

        for domain, port in [  # Valid-looking hosts with a port number
            ('example.com', 80),
            ('12.34.56.78', 443),
            ('[2001:19f0:feee::dead:beef:cafe]', 8080),
        ]:
            host = '%s:%s' % (domain, port)
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            with self.assertRaisesMessage(SuspiciousOperation, msg_suggestion % (host, domain)):
                request.get_host()

        for host in self.poisoned_hosts:
            request = HttpRequest()
            request.META = {'HTTP_HOST': host}
            with self.assertRaisesMessage(SuspiciousOperation, msg_invalid_host % host):
                request.get_host()

        request = HttpRequest()
        request.META = {'HTTP_HOST': "invalid_hostname.com"}
        with self.assertRaisesMessage(SuspiciousOperation, msg_suggestion2 % "invalid_hostname.com"):
            request.get_host()

    def test_split_domain_port_removes_trailing_dot(self):
        domain, port = split_domain_port('example.com.:8080')
        self.assertEqual(domain, 'example.com')
        self.assertEqual(port, '8080')


class BuildAbsoluteURITestCase(SimpleTestCase):
    """
    Regression tests for ticket #18314.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_build_absolute_uri_no_location(self):
        """
        ``request.build_absolute_uri()`` returns the proper value when
        the ``location`` argument is not provided, and ``request.path``
        begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////absolute-uri')
        self.assertEqual(
            request.build_absolute_uri(),
            'http://testserver//absolute-uri'
        )

    def test_build_absolute_uri_absolute_location(self):
        """
        ``request.build_absolute_uri()`` returns the proper value when
        an absolute URL ``location`` argument is provided, and ``request.path``
        begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////absolute-uri')
        self.assertEqual(
            request.build_absolute_uri(location='http://example.com/?foo=bar'),
            'http://example.com/?foo=bar'
        )

    def test_build_absolute_uri_schema_relative_location(self):
        """
        ``request.build_absolute_uri()`` returns the proper value when
        a schema-relative URL ``location`` argument is provided, and
        ``request.path`` begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////absolute-uri')
        self.assertEqual(
            request.build_absolute_uri(location='//example.com/?foo=bar'),
            'http://example.com/?foo=bar'
        )

    def test_build_absolute_uri_relative_location(self):
        """
        ``request.build_absolute_uri()`` returns the proper value when
        a relative URL ``location`` argument is provided, and ``request.path``
        begins with //.
        """
        # //// is needed to create a request with a path beginning with //
        request = self.factory.get('////absolute-uri')
        self.assertEqual(
            request.build_absolute_uri(location='/foo/bar/'),
            'http://testserver/foo/bar/'
        )
