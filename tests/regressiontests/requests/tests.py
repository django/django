import time
from datetime import datetime, timedelta
from StringIO import StringIO

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

        # Read a number of characters greater than the stream has to offer
        stream = LimitedStream(StringIO('test'), 2)
        self.assertEqual(stream.read(5), 'te')

        # Read sequentially from a stream
        stream = LimitedStream(StringIO('12345678'), 8)
        self.assertEqual(stream.read(5), '12345')
        self.assertEqual(stream.read(5), '678')

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

    def test_read_by_lines(self):
        request = WSGIRequest({'REQUEST_METHOD': 'POST', 'wsgi.input': StringIO('name=value')})
        self.assertEqual(list(request), ['name=value'])
