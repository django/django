# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urls import URL
from django.test import SimpleTestCase

path_data = (
    # format: (path, query_string, fragment, expected)
    ('/test/', 'query=true', 'fragment', '/test/?query=true#fragment'),
    # and empty path still returns a slash
    ('', '', '', '/'),
    # ?, = and ; in the path must be encoded
    ('/test/?=;', '', '', '/test/%3F%3D%3B'),
    # other "reserved" characters don't have to be encoded
    ('/test/@&$', '', '', '/test/@&$'),
    # # in query string must be encoded
    ('/test/', 'query=#hashtag', 'fragment', '/test/?query=%23hashtag#fragment'),
    # / and ? in query string are allowed
    ('/test/', 'query/string=what?', '', '/test/?query/string=what?'),
    # # in fragment is allowed
    ('/test/', '', '#fragment#', '/test/##fragment#'),
    # characters outside ASCII range are encoded in the path
    ('/I ♥ Django/', '', '', '/I%20%E2%99%A5%20Django/'),
    # and in the query string
    ('/test/', 'django=♥', '', '/test/?django=%E2%99%A5'),
    # and in the fragment
    ('/test/', '', '♥', '/test/#%E2%99%A5'),
)


url_data = (
    # format: (scheme, host, path, query, fragment, expected)
    ('http', 'example.org', '/', '', '', 'http://example.org/'),
    ('https', 'example.org', '/test/', 'q', 'fragment', 'https://example.org/test/?q#fragment'),
    ('', 'example.org', '', 'q', 'fragment', '//example.org/?q#fragment'),
    ('http', '', '/test/', '', '', 'http:///test/'),
)


class URLTests(SimpleTestCase):
    def test_url_path(self):
        for path, query, fragment, expected in path_data:
            url = URL(path=path, query_string=query, fragment=fragment)
            self.assertEqual(
                str(url), expected,
                "URL(path=%r, query_string=%r, fragment=%r) does not match %r" %
                (path, query, fragment, expected),
            )

    def test_full_url(self):
        for scheme, host, path, query, fragment, expected in url_data:
            url = URL(scheme, host, path, query, fragment)
            self.assertEqual(
                str(url), expected,
                "URL(%r, %r, %r, %r, %r) does not match %r" %
                (scheme, host, path, query, fragment, expected)
            )
