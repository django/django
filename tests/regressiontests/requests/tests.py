import time
from datetime import datetime, timedelta
from StringIO import StringIO

from django.conf import settings
from django.core.handlers.modpython import ModPythonRequest
from django.core.handlers.wsgi import WSGIRequest, LimitedStream
from django.http import HttpRequest, HttpResponse, parse_cookie
from django.utils import unittest
from django.utils.http import cookie_date


class RequestsTests(unittest.TestCase):
    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_wsgirequest(self):
        request = WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus', 'wsgi.input': StringIO('')})
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(set(request.META.keys()), set(['PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME', 'wsgi.input']))
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')

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

    def test_http_get_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = False

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_X_FORWARDED_HOST': u'forward.com',
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is ignored.
            self.assertEqual(request.get_host(), 'example.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST

    def test_http_get_host_with_x_forwarded_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = True

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_X_FORWARDED_HOST': u'forward.com',
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is obeyed.
            self.assertEqual(request.get_host(), 'forward.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST

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
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        self.assertEqual(request.read(), 'name=value')

    def test_read_after_value(self):
        """
        Reading from request is allowed after accessing request contents as
        POST or raw_post_data.
        """
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        self.assertEqual(request.POST, {u'name': [u'value']})
        self.assertEqual(request.raw_post_data, 'name=value')
        self.assertEqual(request.read(), 'name=value')

    def test_value_after_read(self):
        """
        Construction of POST or raw_post_data is not allowed after reading
        from request.
        """
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        self.assertEqual(request.read(2), 'na')
        self.assertRaises(Exception, lambda: request.raw_post_data)
        self.assertEqual(request.POST, {})

    def test_raw_post_data_after_POST_multipart(self):
        """
        Reading raw_post_data after parsing multipart is not allowed
        """
        # Because multipart is used for large amounts fo data i.e. file uploads,
        # we don't want the data held in memory twice, and we don't want to
        # silence the error by setting raw_post_data = '' either.
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
        self.assertRaises(Exception, lambda: request.raw_post_data)

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
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        self.assertEqual(list(request), ['name=value'])

    def test_POST_after_raw_post_data_read(self):
        """
        POST should be populated even if raw_post_data is read first
        """
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        raw_data = request.raw_post_data
        self.assertEqual(request.POST, {u'name': [u'value']})

    def test_POST_after_raw_post_data_read_and_stream_read(self):
        """
        POST should be populated even if raw_post_data is read first, and then
        the stream is read second.
        """
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        raw_data = request.raw_post_data
        self.assertEqual(request.read(1), u'n')
        self.assertEqual(request.POST, {u'name': [u'value']})

    def test_POST_after_raw_post_data_read_and_stream_read_multipart(self):
        """
        POST should be populated even if raw_post_data is read first, and then
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
        raw_data = request.raw_post_data
        # Consume enough data to mess up the parsing:
        self.assertEqual(request.read(13), u'--boundary\r\nC')
        self.assertEqual(request.POST, {u'name': [u'value']})
