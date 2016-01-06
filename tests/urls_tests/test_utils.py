# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.test.client import RequestFactory
from django.urls import URL

path_data = (
    # format: (path, query_string, fragment, repr, expected)
    ('/test/', 'query=true', 'fragment', "<URL '/test/?query=true#fragment'>", '/test/?query=true#fragment'),
    # and empty url returns an empty string
    ('', '', '', "<URL ''>", ''),
    # special characters? no problem.
    ('/test/?=;@&$', '', '', "<URL '/test/%3F=;@&$'>", '/test/%3F=;@&$'),
    # # in query string must be encoded
    (
        '/test/', 'query=#hashtag', 'fragment', "<URL '/test/?query=%23hashtag#fragment'>",
        '/test/?query=%23hashtag#fragment',
    ),
    # / and ? in query string are allowed
    ('/test/', 'query/string=what?', '', "<URL '/test/?query/string=what?'>", '/test/?query/string=what?'),
    # # in fragment is allowed
    ('/test/', '', '#fragment#', "<URL '/test/##fragment#'>", '/test/##fragment#'),
    # characters outside ASCII range are encoded in the path
    ('/I ♥ Django/', '', '', "<URL '/I%20%E2%99%A5%20Django/'>", '/I%20%E2%99%A5%20Django/'),
    # and in the query string
    ('/test/', 'django=♥', '', "<URL '/test/?django=%E2%99%A5'>", '/test/?django=%E2%99%A5'),
    # and in the fragment
    ('/test/', '', '♥', "<URL '/test/#%E2%99%A5'>", '/test/#%E2%99%A5'),
)


url_data = (
    # format: (scheme, host, path, query, fragment, expected)
    ('http', 'example.org', '/', '', '', 'http://example.org/'),
    ('https', 'example.org', '/test/', 'q', 'fragment', 'https://example.org/test/?q#fragment'),
    ('', 'example.org', '/', 'q', 'fragment', '//example.org/?q#fragment'),
    ('http', '', '/test/', '', '', 'http:///test/'),
)


class URLTests(SimpleTestCase):
    def test_url_path(self):
        for path, query, fragment, url_repr, expected in path_data:
            url = URL(path=path, query_string=query, fragment=fragment)
            self.assertEqual(
                str(url), expected,
                "URL(path=%r, query_string=%r, fragment=%r) does not match %r" %
                (path, query, fragment, expected),
            )
            self.assertEqual(repr(url), url_repr)

    def test_full_url(self):
        for scheme, host, path, query, fragment, expected in url_data:
            url = URL(scheme, host, path, query, fragment)
            self.assertEqual(
                str(url), expected,
                "URL(%r, %r, %r, %r, %r) does not match %r" %
                (scheme, host, path, query, fragment, expected)
            )

    def test_from_location(self):
        url = URL.from_location('http://example.org/test/?query=now#fragment')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'example.org')
        self.assertEqual(url.path, '/test/')
        self.assertEqual(url.query_string, 'query=now')
        self.assertEqual(url.fragment, 'fragment')

    def test_from_request(self):
        request = RequestFactory().get('/test/?query=now#fragment')
        url = URL.from_request(request)
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'testserver')
        self.assertEqual(url.path, '/test/')
        self.assertEqual(url.query_string, 'query=now')
        # HttpRequest does not capture the fragment
        self.assertEqual(url.fragment, '')

    def test_url_copy(self):
        url = URL('https', 'example.org:8443', '/test/path/', 'copy=1', 'results')
        copied_url = url.copy()
        self.assertIsNot(url, copied_url)
        self.assertEqual(url.scheme, copied_url.scheme)
        self.assertEqual(url.host, copied_url.host)
        self.assertEqual(url.path, copied_url.path)
        self.assertEqual(url.query_string, copied_url.query_string)
        self.assertEqual(url.fragment, copied_url.fragment)
