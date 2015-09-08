from __future__ import unicode_literals

import sys
import unittest
from datetime import datetime

from django.utils import http, six
from django.utils.datastructures import MultiValueDict


class TestUtilsHttp(unittest.TestCase):

    def test_same_origin_true(self):
        # Identical
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com/'))
        # One with trailing slash - see #15617
        self.assertTrue(http.same_origin('http://foo.com', 'http://foo.com/'))
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com'))
        # With port
        self.assertTrue(http.same_origin('https://foo.com:8000', 'https://foo.com:8000/'))
        # No port given but according to RFC6454 still the same origin
        self.assertTrue(http.same_origin('http://foo.com', 'http://foo.com:80/'))
        self.assertTrue(http.same_origin('https://foo.com', 'https://foo.com:443/'))

    def test_same_origin_false(self):
        # Different scheme
        self.assertFalse(http.same_origin('http://foo.com', 'https://foo.com'))
        # Different host
        self.assertFalse(http.same_origin('http://foo.com', 'http://goo.com'))
        # Different host again
        self.assertFalse(http.same_origin('http://foo.com', 'http://foo.com.evil.com'))
        # Different port
        self.assertFalse(http.same_origin('http://foo.com:8000', 'http://foo.com:8001'))
        # No port given
        self.assertFalse(http.same_origin('http://foo.com', 'http://foo.com:8000/'))
        self.assertFalse(http.same_origin('https://foo.com', 'https://foo.com:8000/'))

    def test_urlencode(self):
        # 2-tuples (the norm)
        result = http.urlencode((('a', 1), ('b', 2), ('c', 3)))
        self.assertEqual(result, 'a=1&b=2&c=3')

        # A dictionary
        result = http.urlencode({'a': 1, 'b': 2, 'c': 3})
        acceptable_results = [
            # Need to allow all of these as dictionaries have to be treated as
            # unordered
            'a=1&b=2&c=3',
            'a=1&c=3&b=2',
            'b=2&a=1&c=3',
            'b=2&c=3&a=1',
            'c=3&a=1&b=2',
            'c=3&b=2&a=1'
        ]
        self.assertIn(result, acceptable_results)
        result = http.urlencode({'a': [1, 2]}, doseq=False)
        self.assertEqual(result, 'a=%5B%271%27%2C+%272%27%5D')
        result = http.urlencode({'a': [1, 2]}, doseq=True)
        self.assertEqual(result, 'a=1&a=2')
        result = http.urlencode({'a': []}, doseq=True)
        self.assertEqual(result, '')

        # A MultiValueDict
        result = http.urlencode(MultiValueDict({
            'name': ['Adrian', 'Simon'],
            'position': ['Developer']
        }), doseq=True)
        acceptable_results = [
            # MultiValueDicts are similarly unordered
            'name=Adrian&name=Simon&position=Developer',
            'position=Developer&name=Adrian&name=Simon'
        ]
        self.assertIn(result, acceptable_results)

    def test_base36(self):
        # reciprocity works
        for n in [0, 1, 1000, 1000000]:
            self.assertEqual(n, http.base36_to_int(http.int_to_base36(n)))
        if six.PY2:
            self.assertEqual(sys.maxint, http.base36_to_int(http.int_to_base36(sys.maxint)))

        # bad input
        self.assertRaises(ValueError, http.int_to_base36, -1)
        if six.PY2:
            self.assertRaises(ValueError, http.int_to_base36, sys.maxint + 1)
        for n in ['1', 'foo', {1: 2}, (1, 2, 3), 3.141]:
            self.assertRaises(TypeError, http.int_to_base36, n)

        for n in ['#', ' ']:
            self.assertRaises(ValueError, http.base36_to_int, n)
        for n in [123, {1: 2}, (1, 2, 3), 3.141]:
            self.assertRaises(TypeError, http.base36_to_int, n)

        # more explicit output testing
        for n, b36 in [(0, '0'), (1, '1'), (42, '16'), (818469960, 'django')]:
            self.assertEqual(http.int_to_base36(n), b36)
            self.assertEqual(http.base36_to_int(b36), n)

    def test_is_safe_url(self):
        for bad_url in ('http://example.com',
                        'http:///example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        r'\\example.com',
                        r'\\\example.com',
                        r'/\\/example.com',
                        r'\\\example.com',
                        r'\\example.com',
                        r'\\//example.com',
                        r'/\/example.com',
                        r'\/example.com',
                        r'/\example.com',
                        'http:///example.com',
                        'http:/\//example.com',
                        'http:\/example.com',
                        'http:/\example.com',
                        'javascript:alert("XSS")',
                        '\njavascript:alert(x)',
                        '\x08//example.com',
                        '\n'):
            self.assertFalse(http.is_safe_url(bad_url, host='testserver'), "%s should be blocked" % bad_url)
        for good_url in ('/view/?param=http://example.com',
                     '/view/?param=https://example.com',
                     '/view?param=ftp://exampel.com',
                     'view/?param=//example.com',
                     'https://testserver/',
                     'HTTPS://testserver/',
                     '//testserver/',
                     '/url%20with%20spaces/'):
            self.assertTrue(http.is_safe_url(good_url, host='testserver'), "%s should be allowed" % good_url)

    def test_urlsafe_base64_roundtrip(self):
        bytestring = b'foo'
        encoded = http.urlsafe_base64_encode(bytestring)
        decoded = http.urlsafe_base64_decode(encoded)
        self.assertEqual(bytestring, decoded)

    def test_urlquote(self):
        self.assertEqual(http.urlquote('Paris & Orl\xe9ans'),
            'Paris%20%26%20Orl%C3%A9ans')
        self.assertEqual(http.urlquote('Paris & Orl\xe9ans', safe="&"),
            'Paris%20&%20Orl%C3%A9ans')
        self.assertEqual(
            http.urlunquote('Paris%20%26%20Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(
            http.urlunquote('Paris%20&%20Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(http.urlquote_plus('Paris & Orl\xe9ans'),
            'Paris+%26+Orl%C3%A9ans')
        self.assertEqual(http.urlquote_plus('Paris & Orl\xe9ans', safe="&"),
            'Paris+&+Orl%C3%A9ans')
        self.assertEqual(
            http.urlunquote_plus('Paris+%26+Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')
        self.assertEqual(
            http.urlunquote_plus('Paris+&+Orl%C3%A9ans'),
            'Paris & Orl\xe9ans')


class ETagProcessingTests(unittest.TestCase):
    def test_parsing(self):
        etags = http.parse_etags(r'"", "etag", "e\"t\"ag", "e\\tag", W/"weak"')
        self.assertEqual(etags, ['', 'etag', 'e"t"ag', r'e\tag', 'weak'])

    def test_quoting(self):
        quoted_etag = http.quote_etag(r'e\t"ag')
        self.assertEqual(quoted_etag, r'"e\\t\"ag"')


class HttpDateProcessingTests(unittest.TestCase):
    def test_http_date(self):
        t = 1167616461.0
        self.assertEqual(http.http_date(t), 'Mon, 01 Jan 2007 01:54:21 GMT')

    def test_cookie_date(self):
        t = 1167616461.0
        self.assertEqual(http.cookie_date(t), 'Mon, 01-Jan-2007 01:54:21 GMT')

    def test_parsing_rfc1123(self):
        parsed = http.parse_http_date('Sun, 06 Nov 1994 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 6, 8, 49, 37))

    def test_parsing_rfc850(self):
        parsed = http.parse_http_date('Sunday, 06-Nov-94 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 6, 8, 49, 37))

    def test_parsing_asctime(self):
        parsed = http.parse_http_date('Sun Nov  6 08:49:37 1994')
        self.assertEqual(datetime.utcfromtimestamp(parsed),
                         datetime(1994, 11, 6, 8, 49, 37))
