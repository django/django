import unittest
from datetime import datetime

from django.test import ignore_warnings
from django.utils import http
from django.utils.datastructures import MultiValueDict
from django.utils.deprecation import RemovedInDjango21Warning


class TestUtilsHttp(unittest.TestCase):

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

        # bad input
        with self.assertRaises(ValueError):
            http.int_to_base36(-1)
        for n in ['1', 'foo', {1: 2}, (1, 2, 3), 3.141]:
            with self.assertRaises(TypeError):
                http.int_to_base36(n)

        for n in ['#', ' ']:
            with self.assertRaises(ValueError):
                http.base36_to_int(n)
        for n in [123, {1: 2}, (1, 2, 3), 3.141]:
            with self.assertRaises(TypeError):
                http.base36_to_int(n)

        # more explicit output testing
        for n, b36 in [(0, '0'), (1, '1'), (42, '16'), (818469960, 'django')]:
            self.assertEqual(http.int_to_base36(n), b36)
            self.assertEqual(http.base36_to_int(b36), n)

    def test_is_safe_url(self):
        bad_urls = (
            'http://example.com',
            'http:///example.com',
            'https://example.com',
            'ftp://example.com',
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
            r'http:/\//example.com',
            r'http:\/example.com',
            r'http:/\example.com',
            'javascript:alert("XSS")',
            '\njavascript:alert(x)',
            '\x08//example.com',
            r'http://otherserver\@example.com',
            r'http:\\testserver\@example.com',
            r'http://testserver\me:pass@example.com',
            r'http://testserver\@example.com',
            r'http:\\testserver\confirm\me@example.com',
            '\n',
        )
        for bad_url in bad_urls:
            with ignore_warnings(category=RemovedInDjango21Warning):
                self.assertFalse(http.is_safe_url(bad_url, host='testserver'), "%s should be blocked" % bad_url)
            self.assertFalse(
                http.is_safe_url(bad_url, allowed_hosts={'testserver', 'testserver2'}),
                "%s should be blocked" % bad_url,
            )

        good_urls = (
            '/view/?param=http://example.com',
            '/view/?param=https://example.com',
            '/view?param=ftp://example.com',
            'view/?param=//example.com',
            'https://testserver/',
            'HTTPS://testserver/',
            '//testserver/',
            'http://testserver/confirm?email=me@example.com',
            '/url%20with%20spaces/',
        )
        for good_url in good_urls:
            with ignore_warnings(category=RemovedInDjango21Warning):
                self.assertTrue(http.is_safe_url(good_url, host='testserver'), "%s should be allowed" % good_url)
            self.assertTrue(
                http.is_safe_url(good_url, allowed_hosts={'otherserver', 'testserver'}),
                "%s should be allowed" % good_url,
            )

        # Valid basic auth credentials are allowed.
        self.assertTrue(http.is_safe_url(r'http://user:pass@testserver/', allowed_hosts={'user:pass@testserver'}))
        # A path without host is allowed.
        self.assertTrue(http.is_safe_url('/confirm/me@example.com'))
        # Basic auth without host is not allowed.
        self.assertFalse(http.is_safe_url(r'http://testserver\@example.com'))

    def test_is_safe_url_secure_param_https_urls(self):
        secure_urls = (
            'https://example.com/p',
            'HTTPS://example.com/p',
            '/view/?param=http://example.com',
        )
        for url in secure_urls:
            self.assertTrue(http.is_safe_url(url, allowed_hosts={'example.com'}, require_https=True))

    def test_is_safe_url_secure_param_non_https_urls(self):
        not_secure_urls = (
            'http://example.com/p',
            'ftp://example.com/p',
            '//example.com/p',
        )
        for url in not_secure_urls:
            self.assertFalse(http.is_safe_url(url, allowed_hosts={'example.com'}, require_https=True))

    def test_urlsafe_base64_roundtrip(self):
        bytestring = b'foo'
        encoded = http.urlsafe_base64_encode(bytestring)
        decoded = http.urlsafe_base64_decode(encoded)
        self.assertEqual(bytestring, decoded)

    def test_urlquote(self):
        self.assertEqual(http.urlquote('Paris & Orl\xe9ans'), 'Paris%20%26%20Orl%C3%A9ans')
        self.assertEqual(http.urlquote('Paris & Orl\xe9ans', safe="&"), 'Paris%20&%20Orl%C3%A9ans')
        self.assertEqual(http.urlunquote('Paris%20%26%20Orl%C3%A9ans'), 'Paris & Orl\xe9ans')
        self.assertEqual(http.urlunquote('Paris%20&%20Orl%C3%A9ans'), 'Paris & Orl\xe9ans')
        self.assertEqual(http.urlquote_plus('Paris & Orl\xe9ans'), 'Paris+%26+Orl%C3%A9ans')
        self.assertEqual(http.urlquote_plus('Paris & Orl\xe9ans', safe="&"), 'Paris+&+Orl%C3%A9ans')
        self.assertEqual(http.urlunquote_plus('Paris+%26+Orl%C3%A9ans'), 'Paris & Orl\xe9ans')
        self.assertEqual(http.urlunquote_plus('Paris+&+Orl%C3%A9ans'), 'Paris & Orl\xe9ans')

    def test_is_same_domain_good(self):
        for pair in (
            ('example.com', 'example.com'),
            ('example.com', '.example.com'),
            ('foo.example.com', '.example.com'),
            ('example.com:8888', 'example.com:8888'),
            ('example.com:8888', '.example.com:8888'),
            ('foo.example.com:8888', '.example.com:8888'),
        ):
            self.assertTrue(http.is_same_domain(*pair))

    def test_is_same_domain_bad(self):
        for pair in (
            ('example2.com', 'example.com'),
            ('foo.example.com', 'example.com'),
            ('example.com:9999', 'example.com:8888'),
        ):
            self.assertFalse(http.is_same_domain(*pair))


class ETagProcessingTests(unittest.TestCase):
    def test_parsing(self):
        self.assertEqual(
            http.parse_etags(r'"" ,  "etag", "e\\tag", W/"weak"'),
            ['""', '"etag"', r'"e\\tag"', 'W/"weak"']
        )
        self.assertEqual(http.parse_etags('*'), ['*'])

        # Ignore RFC 2616 ETags that are invalid according to RFC 7232.
        self.assertEqual(http.parse_etags(r'"etag", "e\"t\"ag"'), ['"etag"'])

    def test_quoting(self):
        self.assertEqual(http.quote_etag('etag'), '"etag"')  # unquoted
        self.assertEqual(http.quote_etag('"etag"'), '"etag"')  # quoted
        self.assertEqual(http.quote_etag('W/"etag"'), 'W/"etag"')  # quoted, weak


class HttpDateProcessingTests(unittest.TestCase):
    def test_http_date(self):
        t = 1167616461.0
        self.assertEqual(http.http_date(t), 'Mon, 01 Jan 2007 01:54:21 GMT')

    def test_cookie_date(self):
        t = 1167616461.0
        self.assertEqual(http.cookie_date(t), 'Mon, 01-Jan-2007 01:54:21 GMT')

    def test_parsing_rfc1123(self):
        parsed = http.parse_http_date('Sun, 06 Nov 1994 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed), datetime(1994, 11, 6, 8, 49, 37))

    def test_parsing_rfc850(self):
        parsed = http.parse_http_date('Sunday, 06-Nov-94 08:49:37 GMT')
        self.assertEqual(datetime.utcfromtimestamp(parsed), datetime(1994, 11, 6, 8, 49, 37))

    def test_parsing_asctime(self):
        parsed = http.parse_http_date('Sun Nov  6 08:49:37 1994')
        self.assertEqual(datetime.utcfromtimestamp(parsed), datetime(1994, 11, 6, 8, 49, 37))
