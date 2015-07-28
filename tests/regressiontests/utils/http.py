import sys

from django.utils import http
from django.utils import unittest
from django.utils.datastructures import MultiValueDict
from django.http import HttpResponse, utils
from django.test import RequestFactory

class TestUtilsHttp(unittest.TestCase):

    def test_same_origin_true(self):
        # Identical
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com/'))
        # One with trailing slash - see #15617
        self.assertTrue(http.same_origin('http://foo.com', 'http://foo.com/'))
        self.assertTrue(http.same_origin('http://foo.com/', 'http://foo.com'))
        # With port
        self.assertTrue(http.same_origin('https://foo.com:8000', 'https://foo.com:8000/'))

    def test_same_origin_false(self):
        # Different scheme
        self.assertFalse(http.same_origin('http://foo.com', 'https://foo.com'))
        # Different host
        self.assertFalse(http.same_origin('http://foo.com', 'http://goo.com'))
        # Different host again
        self.assertFalse(http.same_origin('http://foo.com', 'http://foo.com.evil.com'))
        # Different port
        self.assertFalse(http.same_origin('http://foo.com:8000', 'http://foo.com:8001'))

    def test_urlencode(self):
        # 2-tuples (the norm)
        result = http.urlencode((('a', 1), ('b', 2), ('c', 3)))
        self.assertEqual(result, 'a=1&b=2&c=3')
        # A dictionary
        result = http.urlencode({ 'a': 1, 'b': 2, 'c': 3})
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
        self.assertTrue(result in acceptable_results)
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
        self.assertTrue(result in acceptable_results)

    def test_base36(self):
        # reciprocity works
        for n in [0, 1, 1000, 1000000, sys.maxint]:
            self.assertEqual(n, http.base36_to_int(http.int_to_base36(n)))

        # bad input
        for n in [-1, sys.maxint+1, '1', 'foo', {1:2}, (1,2,3)]:
            self.assertRaises(ValueError, http.int_to_base36, n)

        for n in ['#', ' ']:
            self.assertRaises(ValueError, http.base36_to_int, n)

        for n in [123, {1:2}, (1,2,3)]:
            self.assertRaises(TypeError, http.base36_to_int, n)

        # non-integer input
        self.assertRaises(TypeError, http.int_to_base36, 3.141)

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
                        'javascript:alert("XSS")'
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
